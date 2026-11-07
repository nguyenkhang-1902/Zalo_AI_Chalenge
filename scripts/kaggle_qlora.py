"""QLoRA fine-tune student (Qwen2.5-Coder-7B-Instruct) trên dataset SFT verified của 008.

CHẠY TRÊN KAGGLE GPU (xem specs/008-distill-finetune/KAGGLE.md) — KHÔNG chạy ở máy dev.
Deps (torch/unsloth/trl/peft/datasets) chỉ cài trên Kaggle, KHÔNG thêm vào requirements.txt.

Dataset vào: JSONL, mỗi dòng {"messages": [...], "tools": [...]|null, "meta": {...}} do
`python -m distill.build_dataset` sinh ra. Format bằng apply_chat_template CÓ tools để train khớp
inference (schema_tools mang tên bảng/cột nằm trong tools). train_on_responses_only → chỉ học
assistant-turn (gồm tool_calls + submit_answer), không học phần schema/rulebook trong prompt.
"""
import argparse
import json


def load_rows(path, limit=0):
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    return rows[:limit] if limit else rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="SFT JSONL từ distill.build_dataset")
    ap.add_argument("--out", default="adapter")
    ap.add_argument("--model", default="unsloth/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--max-seq-len", type=int, default=8192)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--smoke", action="store_true", help="20 mẫu, 1 step — kiểm template trước khi train thật")
    a = ap.parse_args()

    from unsloth import FastLanguageModel
    from unsloth.chat_templates import train_on_responses_only
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    model, tok = FastLanguageModel.from_pretrained(
        model_name=a.model, max_seq_length=a.max_seq_len, load_in_4bit=True, dtype=None
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        lora_alpha=16,
        lora_dropout=0.0,
        random_state=42,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    rows = load_rows(a.data, limit=20 if a.smoke else 0)

    def to_text(r):
        kwargs = {"tokenize": False}
        if r.get("tools"):
            kwargs["tools"] = r["tools"]  # đưa tool-definitions vào prompt (khớp inference)
        return {"text": tok.apply_chat_template(r["messages"], **kwargs)}

    ds = Dataset.from_list([to_text(r) for r in rows])

    trainer = SFTTrainer(
        model=model,
        tokenizer=tok,
        train_dataset=ds,
        args=SFTConfig(
            output_dir=a.out,
            dataset_text_field="text",
            max_seq_length=a.max_seq_len,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            max_steps=1 if a.smoke else -1,
            num_train_epochs=a.epochs,
            learning_rate=2e-4,
            seed=42,
            logging_steps=1,
            optim="adamw_8bit",
            report_to="none",
        ),
    )
    # Chỉ tính loss trên assistant-turn. Marker theo chat template Qwen2.5; nếu bản Unsloth khác,
    # chỉnh ở đây (xác nhận bằng --smoke trước).
    trainer = train_on_responses_only(
        trainer,
        instruction_part="<|im_start|>user\n",
        response_part="<|im_start|>assistant\n",
    )
    trainer.train()

    model.save_pretrained(a.out)
    tok.save_pretrained(a.out)
    print("saved LoRA adapter ->", a.out)


if __name__ == "__main__":
    main()
