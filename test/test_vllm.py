import sys
try:
    from vllm import LLM
    print("vllm is installed.")
    llm = LLM(model="baidu/Qianfan-OCR", trust_remote_code=True, dtype="bfloat16", tensor_parallel_size=1)
    print("Success loading Qianfan-OCR in vLLM!")
    sys.exit(0)
except ImportError:
    print("vllm is not installed.")
    sys.exit(1)
except Exception as e:
    print(f"Failed to load in vLLM: {e}")
    sys.exit(1)

if __name__ == '__main__':
    pass
