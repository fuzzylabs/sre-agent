python3 -c "
from transformers import AutoModel
model = AutoModel.from_pretrained('meta-llama/Llama-Prompt-Guard-2-86M')
"

llamafirewall configure

uvicorn  client:app --port 80 --host 0.0.0.0
