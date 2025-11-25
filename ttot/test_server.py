"""
LLM 서버 종합 테스트 스크립트
"""
import requests
import time
import json

BASE_URL = "http://localhost:8002"

def print_test_header(test_name):
    """테스트 헤더 출력"""
    print("\n" + "="*60)
    print(f"🧪 {test_name}")
    print("="*60)

def print_result(success, message):
    """결과 출력"""
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")

def test_health():
    """헬스체크 테스트"""
    print_test_header("테스트 1: 헬스체크")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, "서버 정상 작동")
            print(f"   - 상태: {data['status']}")
            print(f"   - 모델: {data['model']}")
            print(f"   - 문서 수: {data['documents']}")
            return True
        else:
            print_result(False, f"응답 코드: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"연결 실패: {e}")
        return False

def test_simple_chat():
    """간단한 채팅 테스트 (메모리/RAG 없음)"""
    print_test_header("테스트 2: 간단한 채팅 (메모리/RAG 없음)")
    
    payload = {
        "text": "안녕하세요! 간단히 인사해주세요.",
        "user_id": "test_user",
        "use_rag": False,
        "use_memory": False
    }
    
    try:
        print("요청 전송 중...")
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/generate", json=payload, timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"응답 생성 성공 ({elapsed:.2f}초)")
            print(f"   - 질문: {payload['text']}")
            print(f"   - 응답: {data['response']}")
            print(f"   - RAG 사용: {data['rag_used']}")
            return True
        else:
            print_result(False, f"응답 코드: {response.status_code}")
            print(f"   - 에러: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"요청 실패: {e}")
        return False

def test_chat_with_memory():
    """메모리 포함 채팅 테스트"""
    print_test_header("테스트 3: 대화 메모리 테스트")
    
    # 첫 번째 대화
    print("\n1️⃣ 첫 번째 대화: 자기소개")
    payload1 = {
        "text": "내 이름은 테스트유저야. 기억해줘!",
        "user_id": "memory_test_user",
        "use_rag": False,
        "use_memory": True
    }
    
    try:
        response1 = requests.post(f"{BASE_URL}/generate", json=payload1, timeout=30)
        if response1.status_code == 200:
            data1 = response1.json()
            print_result(True, "첫 번째 대화 성공")
            print(f"   - 응답: {data1['response']}")
        else:
            print_result(False, "첫 번째 대화 실패")
            return False
    except Exception as e:
        print_result(False, f"첫 번째 대화 실패: {e}")
        return False
    
    # 잠시 대기
    time.sleep(2)
    
    # 두 번째 대화 (기억 테스트)
    print("\n2️⃣ 두 번째 대화: 이름 기억 확인")
    payload2 = {
        "text": "내 이름이 뭐였지?",
        "user_id": "memory_test_user",
        "use_rag": False,
        "use_memory": True
    }
    
    try:
        response2 = requests.post(f"{BASE_URL}/generate", json=payload2, timeout=30)
        if response2.status_code == 200:
            data2 = response2.json()
            response_text = data2['response'].lower()
            
            # "테스트유저"가 응답에 포함되어 있는지 확인
            if "테스트유저" in response_text or "test" in response_text:
                print_result(True, "이름을 기억하고 있음!")
                print(f"   - 응답: {data2['response']}")
                return True
            else:
                print_result(False, "이름을 기억하지 못함")
                print(f"   - 응답: {data2['response']}")
                return False
        else:
            print_result(False, "두 번째 대화 실패")
            return False
    except Exception as e:
        print_result(False, f"두 번째 대화 실패: {e}")
        return False

def test_document_management():
    """문서 관리 테스트"""
    print_test_header("테스트 4: 문서 추가 및 검색")
    
    # 문서 추가
    print("\n1️⃣ 문서 추가")
    doc_payload = {
        "content": "테스트 정보: 오늘은 LLM 서버 테스트 날입니다. 서버가 정상적으로 작동하는지 확인 중입니다.",
        "metadata": {"source": "test", "type": "info"}
    }
    
    try:
        response = requests.post(f"{BASE_URL}/documents/add", json=doc_payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"문서 추가 성공 (청크 수: {data['chunks_created']})")
        else:
            print_result(False, "문서 추가 실패")
            return False
    except Exception as e:
        print_result(False, f"문서 추가 실패: {e}")
        return False
    
    # 문서 검색
    print("\n2️⃣ 문서 검색")
    try:
        response = requests.get(f"{BASE_URL}/documents/search?query=테스트&k=3", timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print_result(True, f"문서 검색 성공 (결과 수: {len(results)})")
            if results:  # 또는 if data.get('results'):
                print(f"   - 첫 번째 결과: {results[0]['content'][:50]}...")
            return True
        else:
            print_result(False, "문서 검색 실패")
            return False
    except Exception as e:
        print_result(False, f"문서 검색 실패: {e}")
        return False

def test_rag_chat():
    """RAG 포함 채팅 테스트"""
    print_test_header("테스트 5: RAG 기반 채팅")
    
    payload = {
        "text": "LLM 서버 테스트에 대해 알려줘",
        "user_id": "rag_test_user",
        "use_rag": True,
        "use_memory": False
    }
    
    try:
        print("RAG 검색 및 응답 생성 중...")
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/generate", json=payload, timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"RAG 응답 생성 성공 ({elapsed:.2f}초)")
            print(f"   - 질문: {payload['text']}")
            print(f"   - 응답: {data['response'][:100]}...")
            print(f"   - RAG 사용: {data['rag_used']}")
            if data.get('source_documents'):
                print(f"   - 참고 문서 수: {len(data['source_documents'])}")
            return True
        else:
            print_result(False, f"응답 코드: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"요청 실패: {e}")
        return False

def test_stats():
    """통계 조회 테스트"""
    print_test_header("테스트 6: 서버 통계")
    
    try:
        response = requests.get(f"{BASE_URL}/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_result(True, "통계 조회 성공")
            print(f"   - 활성 사용자: {data['active_users']}")
            print(f"   - 총 대화: {data['total_conversations']}")
            print(f"   - DB 문서 수: {data['documents_in_db']}")
            return True
        else:
            print_result(False, f"응답 코드: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"요청 실패: {e}")
        return False

def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "="*60)
    print("🚀 LLM 서버 종합 테스트 시작")
    print("="*60)
    
    # 서버 연결 확인
    print("\n⏳ 서버 연결 확인 중...")
    time.sleep(1)
    
    results = []
    
    # 테스트 실행
    results.append(("헬스체크", test_health()))
    results.append(("간단한 채팅", test_simple_chat()))
    results.append(("대화 메모리", test_chat_with_memory()))
    results.append(("문서 관리", test_document_management()))
    results.append(("RAG 채팅", test_rag_chat()))
    results.append(("서버 통계", test_stats()))
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        icon = "✅" if result else "❌"
        print(f"{icon} {test_name}")
    
    print("\n" + "="*60)
    print(f"총 {total}개 테스트 중 {passed}개 성공")
    success_rate = (passed / total) * 100
    print(f"성공률: {success_rate:.1f}%")
    print("="*60)
    
    if passed == total:
        print("\n🎉 모든 테스트 통과! 서버가 완벽하게 작동합니다!")
    else:
        print(f"\n⚠️ {total - passed}개 테스트 실패. 로그를 확인해주세요.")

if __name__ == "__main__":
    run_all_tests()
