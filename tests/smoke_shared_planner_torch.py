"""Server CPU smoke: real tiny Qwen3 + LoRA, finite updates and frozen base weights."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/research_followup'))
from shared_planner_sft import train


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,default=ROOT/'configs/shared_planner_sft_20261126.json')
    args=parser.parse_args()
    import torch
    from tokenizers import Tokenizer, models, pre_tokenizers
    from transformers import PreTrainedTokenizerFast, Qwen3Config, Qwen3ForCausalLM
    torch.set_num_threads(1)
    torch.manual_seed(42)
    raw=Tokenizer(models.WordLevel({f't{i}':i for i in range(32)},unk_token='t0'))
    raw.pre_tokenizer=pre_tokenizers.Whitespace()
    tok=PreTrainedTokenizerFast(tokenizer_object=raw,unk_token='t0',eos_token='t1',pad_token='t2')
    model=Qwen3ForCausalLM(Qwen3Config(vocab_size=32,hidden_size=32,intermediate_size=64,
        num_hidden_layers=1,num_attention_heads=4,num_key_value_heads=2,head_dim=8,max_position_embeddings=64))
    before={n:p.detach().clone() for n,p in model.named_parameters()}
    cfg=json.loads(args.config.read_text())
    cfg.pop('initial_planner_adapter',None)
    cfg.update(lora_rank=2,lora_alpha=4,gradient_accumulation_steps=2,train_seconds_cap=300)
    examples=[dict(sample_id=str(i),ids=[3,4,5+i,1],labels=[-100,-100,5+i,1],prompt_tokens=2)
              for i in range(4)]
    with tempfile.TemporaryDirectory() as folder:
        trained,receipt=train(model,tok,examples,cfg,Path(folder),time.monotonic())
        # Four microbatches, accumulation=2: exactly two whole optimizer steps.
        assert receipt['status']=='complete' and receipt['steps']==2 and receipt['examples_seen']==4
        assert receipt['tokens']==dict(prompt=8,completion=8)
        assert receipt['adapter_sha256']
        lora=[p for n,p in trained.named_parameters() if 'lora_B' in n]
        assert lora and any(torch.count_nonzero(p).item()>0 for p in lora)
        for n,p in trained.named_parameters():
            if 'lora_' in n: continue
            original=n.removeprefix('base_model.model.').replace('.base_layer.','.')
            assert not p.requires_grad and torch.equal(p.detach(),before[original]), original
        # Reloading an existing adapter must preserve it, not initialize a fresh LoRA.
        expected={n:p.detach().clone() for n,p in trained.named_parameters() if 'lora_' in n}
        another=Qwen3ForCausalLM(trained.config)
        continued=Path(folder)/'continued';continued.mkdir()
        again_cfg={**cfg,'initial_planner_adapter':str(Path(folder)/'adapter'),'learning_rate':0.,'weight_decay':0.}
        loaded,second=train(another,tok,examples,again_cfg,continued,time.monotonic())
        assert second['steps']==2
        for n,p in loaded.named_parameters():
            if 'lora_' in n: assert torch.equal(p.detach(),expected[n]),n
    print(json.dumps(dict(torch_smoke='PASS',optimizer_steps=2,nonzero_lora_updates=True,frozen_base=True)))


if __name__=='__main__': main()
