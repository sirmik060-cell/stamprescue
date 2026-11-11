# tools/convert_lama_to_onnx.py
"""
Конвертация LaMa (big-lama) в ONNX для StampRescue.

Отдельное окружение (нужен torch, тяжёлый):
    pip install simple-lama-inpainting torch onnx

Запуск:
    python tools/convert_lama_to_onnx.py models/lama.onnx
"""
import sys

import torch


def main(out_path):
    from simple_lama_inpainting import SimpleLama
    lama = SimpleLama()
    model = getattr(lama, "model", None) or getattr(lama, "_model", None)
    if model is None:
        raise RuntimeError("Не найден атрибут модели в SimpleLama")
    model.eval()
    for p in model.parameters():
        p.requires_grad = False

    dummy = torch.randn(1, 4, 512, 512)
    torch.onnx.export(
        model, dummy, out_path,
        input_names=["input"], output_names=["output"],
        dynamic_axes={"input": {2: "h", 3: "w"}, "output": {2: "h", 3: "w"}},
        opset_version=14,
    )
    print("OK:", out_path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "models/lama.onnx")