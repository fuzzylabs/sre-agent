echo "Saving llamafirewall model locally, please wait..."

python3 -c "
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)
import os

# Define the model name before using it
model_name = 'meta-llama/Llama-Prompt-Guard-2-86M'

if not os.environ.get('HF_HOME'):
    os.environ['HF_HOME'] = '~/.cache/huggingface'

model_path = os.path.expanduser(
    os.path.join(os.environ['HF_HOME'], model_name.replace('/', '--'))
)

model = AutoModelForSequenceClassification.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Save the model and tokenizer locally
model.save_pretrained(model_path)
tokenizer.save_pretrained(model_path)
"

echo "... done!"

llamafirewall configure

uvicorn client:app --port 80 --host 0.0.0.0
