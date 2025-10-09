CLUSTER=example-slurm # your cluster config
LENGTH=8192 # your target evaluation length
DATA_DIR=/workspace/ns-data # your folder to store data
OUTPUT_DIR=/workspace/ns-results # your folder to store results
MODEL=openai/gpt-oss-120b # your huggingface model
MODEL_NAME=$(basename $MODEL)
MODEL_SERVER_TYPE=vllm # we support vllm, sglang, trtllm, 
MODEL_SERVER_ARGS="--tensor-parallel-size=8 --max-model-len 131072 --trust-remote-code"

## prepare data
ns prepare_data ruler2 \
    --cluster=${CLUSTER} \
    --expname=ruler2-data-${MODEL_NAME}-${LENGTH} \
    --data_dir=${DATA_DIR} \
    --setup=${MODEL_NAME}-${LENGTH} \
    --tokenizer_path=${MODEL} \
    --max_seq_length=${LENGTH}

## evaluate
ns eval \
    --cluster=${CLUSTER} \
    --expname=ruler2-${MODEL_NAME}-${LENGTH} \
    --data_dir=${DATA_DIR} \
    --output_dir=${OUTPUT_DIR} \
    --benchmarks=ruler2.${MODEL_NAME}-${LENGTH} \
    --model=${MODEL} \
    --server_nodes=1 \
    --server_gpus=8 \
    --server_type=${MODEL_SERVER_TYPE} \
    --server_args="${MODEL_SERVER_ARGS}" \
    ++inference.tokens_to_generate=16384 \
    ++inference.top_p=1.0 \
    ++inference.temperature=0.0 \
    ++skip_filled=True

## summarize results
ns summarize_results --cluster=${CLUSTER} ${OUTPUT_DIR}/ruler2.${MODEL_NAME}-${LENGTH}