"""Bounded GRPO mechanics: cached old policy, frozen SFT reference, token PPO clipping.

Outcome-level GRPO (DeepSeekMath, arXiv:2402.03300, section 4.1).
No truncated sampling distribution: temperature=1, top_p=1, top_k=0.
This compact runner is not a reproduction of TRL or a new optimization method.
"""
import math


def group_advantages(rewards, epsilon=1e-4):
    if len(rewards) < 2 or not all(math.isfinite(r) for r in rewards):
        raise ValueError('At least two finite rewards required')
    mean = sum(rewards)/len(rewards)
    std = math.sqrt(sum((r-mean)**2 for r in rewards)/len(rewards))
    return [(r-mean)/(std+epsilon) for r in rewards]


def completion_ids(sequence, prompt_length, eos_token_id):
    """Keep first EOS, remove only padding after EOS; retain capped sequences."""
    result = list(sequence[prompt_length:])
    if eos_token_id in result:
        result = result[:result.index(eos_token_id)+1]
    if not result:
        raise ValueError('Empty completion has no policy-gradient target')
    return result


def load_policy_reference(base, adapter):
    from peft import PeftModel
    model = PeftModel.from_pretrained(base, str(adapter), adapter_name='policy', is_trainable=True)
    model.load_adapter(str(adapter), adapter_name='reference', is_trainable=False)
    set_policy(model, 'policy')
    import torch
    for module in model.modules():
        if isinstance(module, torch.nn.Dropout):
            module.p = 0.0
    return model


def set_policy(model, name):
    if name not in ('policy', 'reference'):
        raise ValueError('Unknown policy')
    model.set_adapter(name)
    # PEFT set_adapter can re-enable gradients: explicitly freeze reference every time.
    for key, parameter in model.named_parameters():
        parameter.requires_grad_(name == 'policy' and '.policy.' in key and 'lora_' in key)


def token_logps(model, prefix, completion):
    """Teacher-forced log p(completion_t | prompt, completion_<t), EOS included."""
    import torch
    ids = torch.tensor([list(prefix)+list(completion)], device=model.device, dtype=torch.long)
    output = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=False)
    logits = output.logits[0, len(prefix)-1:-1].float()
    target = ids[0, len(prefix):]
    if logits.shape[0] != len(completion):
        raise ValueError('Causal completion alignment failed')
    selected = logits.gather(-1, target[:, None]).squeeze(-1)
    return selected-torch.logsumexp(logits, dim=-1)


def clipped_loss(current, old, reference, advantage, *, beta, clip_epsilon):
    """Mean over completion tokens, then callers average equally over sequences."""
    import torch
    if current.ndim != 1 or current.shape != old.shape or current.shape != reference.shape:
        raise ValueError('Token log probabilities must have matching one-dimensional shapes')
    ratio = torch.exp(current-old)
    clipped = ratio.clamp(1-clip_epsilon, 1+clip_epsilon)
    surrogate = torch.minimum(ratio*advantage, clipped*advantage)
    log_reference_ratio = reference-current
    kl = torch.exp(log_reference_ratio)-log_reference_ratio-1
    loss = (-surrogate+beta*kl).mean()
    if not torch.isfinite(loss) or not torch.isfinite(ratio).all():
        raise FloatingPointError('Nonfinite GRPO objective; do not silently clamp log ratios')
    return loss, dict(kl=float(kl.detach().mean()), ratio_mean=float(ratio.detach().mean()),
        ratio_max_abs_delta=float((ratio.detach()-1).abs().max()),
        clipped_fraction=float(((ratio.detach()<1-clip_epsilon)|(ratio.detach()>1+clip_epsilon)).float().mean()))
