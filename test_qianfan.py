import sglang as sgl
import sys

def main():
    try:
        engine = sgl.Engine(model_path="baidu/Qianfan-OCR", dtype="bfloat16", trust_remote_code=True)
        print("Success loading Qianfan-OCR in SGLang!")
        sys.exit(0)
    except Exception as e:
        print(f"Failed to load in SGLang: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
