# coding: utf-8

# 파일 읽기
with open('backend/app/services/dart_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 패치 읽기
with open('backend/app/services/dart_api_patch.py', 'r', encoding='utf-8') as f:
    patch = f.read()

# 이미 추가되었는지 확인
if 'get_metrics_at_date' in content:
    print('이미 함수가 존재합니다')
else:
    # '# 전역 인스턴스' 바로 앞에 함수 삽입
    new_content = content.replace('\n\n# 전역 인스턴스', patch + '\n\n\n# 전역 인스턴스')
    
    # 파일 쓰기
    with open('backend/app/services/dart_api.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print('get_metrics_at_date() 함수 추가 완료')
