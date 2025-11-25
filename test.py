import requests
import time

BASE_URL = "http://127.0.0.1:5001"

print("=" * 60)
print("🔍 서버 연결 진단 시작")
print("=" * 60)

# 1단계: 기본 연결 확인
print("\n1️⃣  기본 연결 확인 (GET /)")
try:
    response = requests.get(f"{BASE_URL}/")
    print(f"✅ 상태 코드: {response.status_code}")
    print(f"📄 응답:\n{response.text}")
    if response.status_code == 200:
        print(f"✅ 데이터: {response.json()}")
except requests.exceptions.ConnectionError:
    print("❌ 서버에 연결할 수 없습니다!")
    print("   해결: 터미널에서 'uvicorn main:app --reload --port 5000' 실행")
    exit()
except Exception as e:
    print(f"❌ 오류: {e}")
    exit()

time.sleep(1)

# 2단계: ATOT 호출
print("\n" + "=" * 60)
print("2️⃣  ATOT 엔드포인트 호출")
print("=" * 60)
try:
    response = requests.get(f"{BASE_URL}/atot")
    print(f"✅ 상태 코드: {response.status_code}")
    print(f"📄 응답 텍스트:\n{response.text}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"✅ JSON 데이터:\n{data}")
        except Exception as e:
            print(f"⚠️  JSON 파싱 실패: {e}")
    else:
        print(f"⚠️  상태 코드 {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ 서버에 연결할 수 없습니다!")
except Exception as e:
    print(f"❌ 오류: {e}")

time.sleep(1)

# 3단계: TTOT 호출
print("\n" + "=" * 60)
print("3️⃣  TTOT 엔드포인트 호출")
print("=" * 60)
try:
    response = requests.get(f"{BASE_URL}/ttot")
    print(f"✅ 상태 코드: {response.status_code}")
    print(f"📄 응답 텍스트:\n{response.text}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"✅ JSON 데이터:\n{data}")
        except Exception as e:
            print(f"⚠️  JSON 파싱 실패: {e}")
    else:
        print(f"⚠️  상태 코드 {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ 서버에 연결할 수 없습니다!")
except Exception as e:
    print(f"❌ 오류: {e}")

time.sleep(1)

# 4단계: 오디오 처리
print("\n" + "=" * 60)
print("4️⃣  오디오 처리 엔드포인트 호출")
print("=" * 60)
try:
    response = requests.post(f"{BASE_URL}/process-audio")
    print(f"✅ 상태 코드: {response.status_code}")
    print(f"📄 응답 텍스트:\n{response.text}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"✅ JSON 데이터:\n{data}")
        except Exception as e:
            print(f"⚠️  JSON 파싱 실패: {e}")
    else:
        print(f"⚠️  상태 코드 {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ 서버에 연결할 수 없습니다!")
except Exception as e:
    print(f"❌ 오류: {e}")

print("\n" + "=" * 60)
print("✅ 진단 완료!")
print("=" * 60)