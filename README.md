# RULERv1 NeMo-Skills Evaluation

## 💡 Requirements

- Clone NeMo-Skills [repo](https://github.com/NVIDIA-NeMo/Skills/tree/main).
- Install NeMo-Skills `cd Skills && pip install -e .`.
- Setup cluster config under folder `Skills/cluster_configs`. 
    - You can create slurm or local config on your preference.
    - Remember to mount the folder you need.

## 🔍 Evaluate long-context LMs
- Make sure your model is supported by either [vLLM](https://github.com/vllm-project/vllm), [SGLang](https://github.com/sgl-project/sglang), or [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM)
- Download model weights from [Huggingface](https://huggingface.co/models).
- Setup environment variables.
```
CLUSTER=example-slurm # your cluster config
LENGTH=8192 # your target evaluation length
DATA_DIR=/workspace/ns-data # your folder to store data
OUTPUT_DIR=/workspace/ns-results # your folder to store results
MODEL=openai/gpt-oss-120b # your huggingface model
MODEL_NAME=$(basename $MODEL)
MODEL_SERVER_TYPE=vllm # we support vllm, sglang, trtllm, 
MODEL_SERVER_ARGS="--tensor-parallel-size=8 --max-model-len 131072 --trust-remote-code"
```
- Generate data using your model tokenizer.
```
ns prepare_data ruler \
    --cluster=${CLUSTER} \
    --expname=rulerv1-data-${MODEL_NAME}-${LENGTH} \
    --data_dir=${DATA_DIR} \
    --setup=${MODEL_NAME}-${LENGTH} \
    --tokenizer_path=${MODEL} \
    --max_seq_length=${LENGTH}
```
- Run evaluation.
```
ns eval \
    --cluster=${CLUSTER} \
    --expname=ruler1-${MODEL_NAME}-${LENGTH} \
    --data_dir=${DATA_DIR} \
    --output_dir=${OUTPUT_DIR} \
    --benchmarks=ruler.${MODEL_NAME}-${LENGTH} \
    --model=${MODEL} \
    --server_nodes=1 \
    --server_gpus=8 \
    --server_type=${MODEL_SERVER_TYPE} \
    --server_args="${MODEL_SERVER_ARGS}" \
    ++inference.tokens_to_generate=4096 \
    ++inference.top_p=1.0 \
    ++inference.temperature=0.0 \
    ++skip_filled=True
```
- Summarize your results.
```
ns summarize_results --cluster=${CLUSTER} ${OUTPUT_DIR}/ruler.${MODEL_NAME}-${LENGTH}
```
- We provide example script in `run_example.sh`

## 🖊️ Notes
- You can change your vllm or sglang container to support your model in your cluster config.
- You can evaluate other popular benchmarks using NeMo-Skills. Please see the [documentation](https://nvidia-nemo.github.io/Skills/).
- Our ruler dataset definition is under [here](https://github.com/NVIDIA-NeMo/Skills/tree/main/nemo_skills/dataset/ruler).