Модель lama.onnx (196 МБ) не хранится в git — файлы >100 МБ GitHub не принимает.

Как получить lama.onnx (три способа):

1. ПРОЩЕ ВСЕГО — из установленной программы:
   скачайте установщик релиза v0.5 (Assets на странице релиза), установите,
   файл лежит в <папка установки>\_internal\models\lama.onnx

2. Конвертировать из оригинальных весов (нужен Python + ~2 ГБ свободно):
   pip install simple-lama-inpainting torch onnx
   python tools/convert_lama_to_onnx.py models/lama.onnx
   Скрипт сам скачает оригинальные веса big-lama.pt (196 МБ) сюда:
   https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt

3. Попросить lama.onnx у разработчика (файл 196 МБ).

После получения просто положите файл в models/ — программа его подхватит.
Файлы image.jpg / mask.png / output_onnx_fp32.png — тестовый вход/выход конвертера,
их проверочный прогон: tools/verify_onnx.py.
