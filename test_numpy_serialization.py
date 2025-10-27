"""
numpy.bool 직렬화 테스트
"""
import json
import numpy as np

# NumpyEncoder 클래스 정의
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, np.datetime64):
            return str(obj)
        return super().default(obj)

# 테스트 데이터
test_data = {
    'float_value': np.float64(3.14),
    'int_value': np.int64(42),
    'bool_value': np.bool_(True),
    'array': np.array([1, 2, 3]),
    'nested': {
        'bool': np.bool_(False),
        'float': np.float32(2.718)
    }
}

print("원본 데이터:")
for key, value in test_data.items():
    print(f"  {key}: {value} (type: {type(value)})")

print("\n1. 일반 json.dumps (에러 발생 예상):")
try:
    result = json.dumps(test_data)
    print(f"  성공: {result}")
except Exception as e:
    print(f"  에러: {e}")

print("\n2. NumpyEncoder 사용:")
try:
    result = json.dumps(test_data, cls=NumpyEncoder)
    print(f"  성공: {result}")

    # 역직렬화 테스트
    parsed = json.loads(result)
    print(f"\n3. 역직렬화 결과:")
    for key, value in parsed.items():
        print(f"  {key}: {value} (type: {type(value)})")
except Exception as e:
    print(f"  에러: {e}")

print("\n✅ 테스트 완료")
