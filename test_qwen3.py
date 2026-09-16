import sglang as sgl
import sys

def main():
    try:
        # Test without AWQ just to see if the architecture is supported
        engine = sgl.Engine(model_path="Qwen/Qwen3-VL-8B-Instruct", dtype="bfloat16")
        print("Success loading Qwen3-VL in SGLang!")
        sys.exit(0)
    except Exception as e:
        print(f"Failed to load in SGLang: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
