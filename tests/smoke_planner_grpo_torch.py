"""Server CPU checks against analytic PPO terms and an actual tiny Qwen3+LoRA."""
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/research_followup'))
from planner_grpo_core import clipped_loss,load_policy_reference,set_policy,token_logps


def main():
    import torch
    from peft import LoraConfig,get_peft_model
    from peft.tuners.lora import model as peft_lora_model
    from transformers import Qwen3Config,Qwen3ForCausalLM,GenerationConfig
    if hasattr(peft_lora_model,'dispatch_torchao'):
        peft_lora_model.dispatch_torchao=lambda *_a,**_k:None
    torch.set_num_threads(1);torch.manual_seed(42)
    # Analytic PPO: positive A and ratio1.5 clips at1.2; negative A and ratio.5 clips at.8.
    for ratio,advantage,expected in [(1.5,1.,-1.2),(.5,-1.,.8)]:
        cur=torch.tensor([ratio]).log().requires_grad_();zero=torch.zeros(1)
        loss,_=clipped_loss(cur,zero,zero,advantage,beta=0.,clip_epsilon=.2)
        assert torch.isclose(loss,torch.tensor(expected),atol=1e-6)
        loss.backward();assert torch.isfinite(cur.grad).all()
    # Analytic k3 at ref/current=2: 2-log(2)-1.
    loss,_=clipped_loss(torch.zeros(1),torch.zeros(1),torch.tensor([2.]).log(),0.,beta=1.,clip_epsilon=.2)
    assert torch.isclose(loss,torch.tensor(1.-__import__('math').log(2.)),atol=1e-6)
    config=Qwen3Config(vocab_size=32,hidden_size=32,intermediate_size=64,num_hidden_layers=1,
        num_attention_heads=4,num_key_value_heads=2,head_dim=8,max_position_embeddings=64)
    base=Qwen3ForCausalLM(config)
    initial=get_peft_model(base,LoraConfig(r=2,lora_alpha=4,lora_dropout=.05,
        target_modules=['q_proj','v_proj'],task_type='CAUSAL_LM'))
    with torch.no_grad():
        for n,p in initial.named_parameters():
            if 'lora_B' in n:p.fill_(.02)
    with tempfile.TemporaryDirectory() as d:
        initial.save_pretrained(d)
        plain=initial.unload()
        model=load_policy_reference(plain,d);model.eval()
        before={n:p.detach().clone() for n,p in model.named_parameters()}
        prefix=[3,4];completion=[6,7,1]
        old=token_logps(model,prefix,completion).detach()
        set_policy(model,'reference')
        with torch.no_grad():ref=token_logps(model,prefix,completion).detach()
        assert torch.equal(old,ref), 'Frozen reference must be the initial SFT adapter'
        set_policy(model,'policy')
        # Independent direct softmax confirms token shift and prompt exclusion.
        ids=torch.tensor([prefix+completion]);logits=model(input_ids=ids,use_cache=False).logits
        manual=torch.log_softmax(logits[0,1:-1].float(),-1)[torch.arange(3),torch.tensor(completion)]
        assert torch.allclose(token_logps(model,prefix,completion),manual,atol=1e-6)
        gen=model.generate(input_ids=torch.tensor([prefix]),
            generation_config=GenerationConfig(do_sample=True,temperature=1.,top_p=1.,top_k=0,
                max_new_tokens=3,eos_token_id=None,pad_token_id=2),return_dict_in_generate=True,output_scores=True)
        tokens=gen.sequences[0,2:].tolist()
        sampled=torch.stack([torch.log_softmax(s.float(),-1)[0,t] for s,t in zip(gen.scores,tokens)])
        assert torch.allclose(sampled,token_logps(model,prefix,tokens),atol=1e-5)
        params=[p for p in model.parameters() if p.requires_grad]
        opt=torch.optim.AdamW(params,lr=.01,weight_decay=0.)
        metrics=[]
        for step in range(2):
            opt.zero_grad(set_to_none=True)
            loss,m=clipped_loss(token_logps(model,prefix,completion),old,ref,1.,beta=.04,clip_epsilon=.2)
            loss.backward();norm=torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True)
            opt.step();metrics.append(m)
        assert metrics[0]['ratio_max_abs_delta']<1e-6
        assert metrics[1]['ratio_max_abs_delta']>1e-5 and metrics[1]['kl']>0
        assert any(not torch.equal(p.detach(),before[n]) for n,p in model.named_parameters() if '.policy.' in n)
        for n,p in model.named_parameters():
            if '.policy.' not in n:assert torch.equal(p.detach(),before[n]),n
            if '.reference.' in n:assert not p.requires_grad and p.grad is None,n
    print(json.dumps(dict(torch_smoke='PASS',causal_alignment=True,sampling_logprob_match=True,
        frozen_sft_reference=True,frozen_base=True,real_policy_updates=2,second_update=metrics[1])))


if __name__=='__main__':main()
