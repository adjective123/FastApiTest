// scripts.js
const API_BASE_URL = ""; // 같은 서버에서 HTML과 API를 같이 쓸 때는 빈 문자열이면 됨
// const API_BASE_URL = "https://192.168.0.37:5001";

document.addEventListener("DOMContentLoaded", () => {
  // ===== 로그인 화면 관련 DOM =====
  const loginScreen   = document.getElementById("loginScreen");
  const loginForm     = document.getElementById("loginForm");
  const loginIdInput  = document.getElementById("loginId");
  const loginPwInput  = document.getElementById("loginPw");
  const loginErrorEl  = document.getElementById("loginError");
  const registerScreen = document.getElementById("registerScreen");
  const goRegisterBtn = document.getElementById("goRegisterBtn");
  const backToLoginBtn = document.getElementById("backToLoginBtn");

  const registerForm = document.getElementById("registerForm");
  const regIdInput = document.getElementById("regId");
  const regPwInput = document.getElementById("regPw");
  const registerErrorEl = document.getElementById("registerError");

  // ===== 홈 / 채팅 화면 관련 DOM =====
  const homeScreen   = document.getElementById("homeScreen");
  const chatScreen   = document.getElementById("app");
  const startChatBtn = document.getElementById("startChatBtn");
  const subiconBtn   = document.getElementById("subiconBtn");

  // 유저 uuid 저장용
  let currentUserUUID = null;
  let currentUserId = null;

  // 로그인 성공 후 메시지 로딩에 쓸 함수(아래에서 할당)
  let loadMessages = null;

  // 모델 선택
  let currentChatMode = "0";

  // ===== 화면 전환 함수 =====
  function showLogin() {
    if (loginScreen)  loginScreen.classList.remove("hidden");
    if (homeScreen)   homeScreen.classList.add("hidden");
    if (chatScreen)   chatScreen.classList.add("hidden");
  }

  function showHome() {
    if (loginScreen)  loginScreen.classList.add("hidden");
    if (homeScreen)   homeScreen.classList.remove("hidden");
    if (chatScreen)   chatScreen.classList.add("hidden");
  }

  let userInput = null; // 아래에서 실제 DOM을 할당

  function showChat() {
    if (loginScreen)  loginScreen.classList.add("hidden");
    if (homeScreen)   homeScreen.classList.add("hidden");
    if (chatScreen)   chatScreen.classList.remove("hidden");

    if (userInput) userInput.focus();
  }

  function showRegister() {
    loginScreen.classList.add("hidden");
    registerScreen.classList.remove("hidden");
    homeScreen.classList.add("hidden");
    chatScreen.classList.add("hidden");
  }

  function backToLogin() {
    loginScreen.classList.remove("hidden");
    registerScreen.classList.add("hidden");
    homeScreen.classList.add("hidden");
    chatScreen.classList.add("hidden");
  }

  // 처음엔 로그인 화면을 보여줌
  showLogin();

  if (startChatBtn) {
    startChatBtn.addEventListener("click", showChat);
  }

  if (subiconBtn) {
    subiconBtn.addEventListener("click", showHome);
  }

  // ===== 로그인 처리 =====
  if (loginForm && loginIdInput && loginPwInput) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const username = loginIdInput.value.trim();
      const password = loginPwInput.value.trim();

      if (!username || !password) return;

      try {
        const res = await fetch(`${API_BASE_URL}/api/login`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ username, password }),
        });

        if (!res.ok) {
          console.error("로그인 요청 실패", res.status);
          if (loginErrorEl) {
            loginErrorEl.textContent = "서버 오류가 발생했습니다.";
            loginErrorEl.classList.remove("hidden");
          }
          return;
        }

        const data = await res.json();

        // uuid 조회

        if (data.success) {
          if (loginErrorEl) loginErrorEl.classList.add("hidden");
          // uuid 저장
          currentUserId = data.username;
          currentUserUUID = await (await fetch(`/api/get_uuid?username=${data.username}`)).json();

          // 로그인 성공 → 홈 화면
          showHome();

          // 로그인 후 기존 메시지 불러오기
          if (typeof loadMessages === "function") {
            loadMessages();
          }
        } else {
          if (loginErrorEl) {
            loginErrorEl.textContent = data.message || "아이디 또는 비밀번호가 올바르지 않습니다.";
            loginErrorEl.classList.remove("hidden");
          }
        }
      } catch (err) {
        console.error("로그인 중 오류", err);
        if (loginErrorEl) {
          loginErrorEl.textContent = "네트워크 오류가 발생했습니다.";
          loginErrorEl.classList.remove("hidden");
        }
      }
    });
  }

  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const id = regIdInput.value.trim();
      const pwd = regPwInput.value.trim();

      if (!id || !pwd) return;

      try {
        const res = await fetch(`${API_BASE_URL}/api/register`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ id, pwd }),
        });

        const data = await res.json();

        if (!data.success) {
          registerErrorEl.textContent = data.message;
          registerErrorEl.classList.remove("hidden");
          return;
        }

        // 회원가입 성공
        alert("회원가입 완료! 로그인해주세요.");
        registerErrorEl.classList.add("hidden");

        // 로그인 화면으로 전환
        backToLogin();

      } catch (err) {
        registerErrorEl.textContent = "네트워크 오류가 발생했습니다.";
        registerErrorEl.classList.remove("hidden");
        console.error(err);
      }
    });
  }


  goRegisterBtn.addEventListener("click", showRegister);
  backToLoginBtn.addEventListener("click", backToLogin);

  // ===== 사이드바 관련 =====
  const settingsBtn     = document.getElementById("settingsBtn");
  const sidebar         = document.getElementById("sidebar");
  const sidebarOverlay  = document.getElementById("sidebarOverlay");
  const sidebarCloseBtn = document.getElementById("sidebarCloseBtn");

  document.querySelectorAll("input[name='chatMode']").forEach((el) => {
    el.addEventListener("change", () => {
      currentChatMode = el.value;
    });
  });

  if (settingsBtn && sidebar && sidebarOverlay && sidebarCloseBtn) {
    function openSidebar() {
      sidebar.classList.add("open");
      sidebarOverlay.classList.add("open");
    }
    function closeSidebar() {
      sidebar.classList.remove("open");
      sidebarOverlay.classList.remove("open");
    }

    settingsBtn.addEventListener("click", openSidebar);
    sidebarCloseBtn.addEventListener("click", closeSidebar);
    sidebarOverlay.addEventListener("click", closeSidebar);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeSidebar();
    });
  }

  // ===== 채팅 관련 DOM =====
  const mainScreen = document.getElementById("mainScreen");
  userInput        = document.getElementById("userTextInput");
  const chatLog    = document.getElementById("chatLog");
  const chatMsgs   = document.getElementById("chatLogMessages");
  const closeBtn   = document.getElementById("chatLogCloseBtn");
  const sendBtn    = document.getElementById("sendBtn");
  const recordBtn  = document.getElementById("recordBtn");

  if (!mainScreen || !userInput || !chatLog || !chatMsgs || !closeBtn) {
    console.warn("채팅 관련 요소를 찾을 수 없습니다.");
    return;
  }

  // ------------------------------
  // 채팅 로그 표시/숨김
  // ------------------------------
  function showChatLog() {
    chatLog.classList.remove("hidden");
    mainScreen.classList.add("with-chat");
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  function hideChatLog() {
    chatLog.classList.add("hidden");
    mainScreen.classList.remove("with-chat");
  }

  // ------------------------------
  // 말풍선 추가 함수
  // ------------------------------
  function addChatMessage(text, who = "me") {
    const row = document.createElement("div");
    row.className = `chatRow ${who}`;

    const bubble = document.createElement("div");
    bubble.className = "chatBubble";

    if (who == "system") {
      bubble.style.backgroundColor = "#ff6b6b";
      bubble.style.color = "#fff";
      bubble.style.fontSize = "0.9em";
      bubble.style.textAlign = "center";
    }

    bubble.textContent = text;

    row.appendChild(bubble);
    chatMsgs.appendChild(row);
    chatLog.scrollTop = chatLog.scrollHeight;
  }
  // ------------------------------
  // 오디오 추가 함수
  // ------------------------------
  function addAudioMessage(src, who = "other") {
    const row = document.createElement("div");
    row.className = `chatRow ${who}`;

    const bubble = document.createElement("div");
    bubble.className = "chatBubble audioBubble";

    // 오디오 엘리먼트 (controls 제거)
    const audio = document.createElement("audio");
    audio.src = src;

    // 재생 상태 아이콘
    const icon = document.createElement("span");
    icon.className = "audioIcon";
    icon.textContent = "■"; // 재생 중 표시

    bubble.appendChild(icon);
    bubble.appendChild(audio);
    row.appendChild(bubble);
    chatMsgs.appendChild(row);

    chatLog.scrollTop = chatLog.scrollHeight;

    // 자동 재생 시도
    audio.play().catch((err) => {
      console.warn("자동재생 실패:", err);
      icon.textContent = "▶"; // 자동재생 안되면 ▶로
    });

    // 재생 시작 → ■
    audio.addEventListener("play", () => {
      icon.textContent = "■";
    });

    // 재생 종료 → ▶
    audio.addEventListener("ended", () => {
      icon.textContent = "▶";
    });

    // 클릭 시 재생/일시정지 토글
    bubble.addEventListener("click", () => {
      if (audio.paused) {
        audio.play();
      } else {
        audio.pause();
        icon.textContent = "▶"; // 일시정지 시 ▶
      }
    });
  }

  // ------------------------------
  // 과거 메시지 불러오기 (로그인 후 사용)
  // ------------------------------
  loadMessages = async function () {
    try {
      const res = await fetch(`${API_BASE_URL}/api/conversation/${currentUserId}`);
      if (!res.ok) {
        console.error("대화 목록 불러오기 실패", res.status);
        return;
      }
      const data = await res.json();

      chatMsgs.innerHTML = "";
      for (const item of data.conversation) {
        // 사용자 입력 시
        if (item.type === "input") {
          addChatMessage(item.text, "me")
        // 응답
        } else if (item.type === "output") {
          addChatMessage(item.text, "other")
        }
      }
      if (data.conversation.length > 0) {
        showChatLog();
      }
    } catch (err) {
      console.error("대화목록 로딩 중 오류", err);
    }
  };

  // ------------------------------
  // 텍스트 입력/전송
  // ------------------------------
  userInput.addEventListener("focus", showChatLog);

  userInput.addEventListener("input", () => {
    if (userInput.value.trim().length > 0) {
      showChatLog();
    }
  });
  // ------------------------------
  // UI 잠금/해제 함수
  // ------------------------------
  function lockUI() {
    isProcessingMessage = true;
    if (userInput) {
      userInput.disabled = true;
      userInput.style.opacity = "0.6";
      userInput.placeholder = "답변 생성 중...";
    }
    if (sendBtn) {
      sendBtn.disabled = true;
      sendBtn.style.opacity = "0.6";
    }
    if (recordBtn) {
      recordBtn.disabled = true;
      recordBtn.style.opacity = "0.6";
    }

    const loadingMsg = document.createElement("div");
    loadingMsg.id = "loadingMessage";
    loadingMsg.className = "chatRow other";
    loadingMsg.innerHTML = `
    <div class="chatBubble" style="opacity: 0.7;">
      <span class="loadingDots">답변 생성 중</span>
    </div>
  ` ;
    chatMsgs.appendChild(loadingMsg);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  function unlockUI() {
    isProcessingMessage = false;
    if (userInput) {
      userInput.disabled = false;
      userInput.style.opacity = "1";
      userInput.placeholder = "텍스트를 입력하세요";
      userInput.focus(); // 자동 포커스
    }
    if (sendBtn) {
      sendBtn.disabled = false;
      sendBtn.style.opacity = "1";
    }
    if (recordBtn) {
      recordBtn.disabled = false;
      recordBtn.style.opacity = "1";
    }
    const loadingMsg = document.getElementById("loadingMessage");
    if (loadingMsg) {
      loadingMsg.remove();
    }
  }

  async function sendMessage(result = null) {
    const text = result ?? userInput.value.trim();
    if (!text) return;

    if (isProcessingMessage) {
      console.warn("⚠️ 이미 메시지 처리 중입니다.");
      return;
    }

    lockUI()

    // 1) 먼저 내 메시지를 바로 UI에 표시
    addChatMessage(text, "me");
    showChatLog();
    userInput.value = "";

    try {
      // 2) 서버에 전송
      const roomId = currentUserId || "test";
      const res = await fetch(`${API_BASE_URL}/api/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          room_id: roomId,
          text: text,
          client_type: "web",
          user_id: currentUserId || "test",
          mode: currentChatMode
        }),
      });

      if (!res.ok) {
        console.error("메시지 전송 실패", res.status);
        // 필요하면 여기서 에러 말풍선 하나 더 추가해도 됨
        return;
      }

      const saved = await res.json();
      console.log("saved:", saved);

      reply_audio_path = `/wav_files/${currentUserUUID}/received_audio.wav`;
      console.log("reply_audio_path:", reply_audio_path);

      // 3) 서버 B에서 처리한 답장만 나중에 표시
      if (saved.reply_text) {
        addChatMessage(saved.reply_text, "other");
        addAudioMessage(reply_audio_path, "other");
      }
    } catch (err) {
      console.error("메시지 전송 중 오류", err);
      addChatMessage("서버 연결 오류가 발생했습니다.", "system");
      // 여기서도 "전송 중 오류" 같은 시스템 메시지 띄우고 싶으면 추가 가능
    } finally {
      unlockUI()
    }
  }

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  });

  if (sendBtn) {
    sendBtn.addEventListener("click", () => {
      sendMessage();
      userInput.focus();
    });
  }

  closeBtn.addEventListener("click", hideChatLog);

  document.addEventListener("click", (e) => {
    if (chatLog.classList.contains("hidden")) return;

    const isInChat  = chatLog.contains(e.target);
    const isInput   = (e.target === userInput);
    const isSend    = sendBtn && sendBtn.contains(e.target);
    const isRecord  = recordBtn && recordBtn.contains(e.target);

    if (!isInChat && !isInput && !isSend && !isRecord) {
      hideChatLog();
    }
  });

  // ------------------------------
  // 🎙️ 실시간 녹음 스트리밍
  //   /start + /ingest-chunk 구조
  // ------------------------------
  let audioContext = null;
  let stream       = null;
  let workletNode  = null;
  let isRecordingAudio = false;
  let isProcessingMessage = false;
  let recSessionId = null;
  let recSeq       = 0;
  let recordingTimeout = null; // ✅ 추가: 녹음 타임아웃 관리용

  // 세션 시작 (서버A → 서버B /start 프록시)
  async function startAudioSession() {
    try {
      const res = await fetch(`${API_BASE_URL}/start`, { method: "POST" });
      if (!res.ok) {
        console.error("오디오 세션 생성 실패", res.status);
        return null;
      }
      const data = await res.json();
      console.log("audio sessionId:", data.sessionId);
      return data.sessionId;
    } catch (err) {
      console.error("오디오 세션 생성 중 오류", err);
      return null;
    }
  }

  // PCM 청크 전송 (/ingest-chunk)
  async function sendPCMChunk(buffer) {
    if (!isRecordingAudio || !recSessionId) return;

    const blob = new Blob([buffer], { type: "application/octet-stream" });
    const formData = new FormData();
    formData.append("sessionId", recSessionId);
    formData.append("chunk", blob, `chunk-${recSeq++}.raw`);
    formData.append("mode", "chunk");

    try {
      const res = await fetch(`${API_BASE_URL}/ingest-chunk`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        console.error("청크 전송 실패", res.status);
        return;
      }
      const data = await res.json();
      console.log("audio resp:", data);

      // data.status: "Silent" | "Speech" | "Finished" | "Error"
      // ===== 원본 코드 (주석 처리) =====
      // if (data.status === "Finished" && data.text) {
      //   // 최종 인식 결과를 나의 메시지로 표시
      //   await sendMessage(data.text);
      // }
      
      // ===== 수정된 코드: 음성 인식 완료 후 자동 녹음 중지 =====
      if (data.status === "Finished" && data.text) {
        // 최종 인식 결과를 나의 메시지로 표시
        await sendMessage(data.text);
        
        // ✅ 음성 인식 완료 후 녹음 자동 중지
        stopRecordingAudio("voice-recognition-finished");
        console.log("✅ 음성 인식 완료 - 녹음 자동 중지");
      } else if (data.status === "Error") {
        // ✅ 에러 발생 시에도 녹음 중지
        stopRecordingAudio("voice-recognition-error");
        console.error("❌ 음성 인식 오류 - 녹음 중지");
        addChatMessage("음성 인식 중 오류가 발생했습니다.", "system");
      }
    } catch (err) {
      console.error("청크 업로드 중 오류", err);
    }
  }

  // 녹음 시작
  async function startRecordingAudio() {
    if (isRecordingAudio) return;

    try {
      // 1) 마이크 스트림
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // 2) AudioContext + AudioWorklet
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      await audioContext.audioWorklet.addModule("/static/processor.js?v=" + Date.now());

      const source = audioContext.createMediaStreamSource(stream);
      workletNode = new AudioWorkletNode(audioContext, "audio-stream-processor");

      source.connect(workletNode);

      // Worklet -> JS
      workletNode.port.onmessage = (event) => {
        // event.data는 Int16Array의 buffer (ArrayBuffer)
        sendPCMChunk(event.data);
      };

      // 3) 서버 세션 생성
      recSessionId = await startAudioSession();
      if (!recSessionId) {
        throw new Error("세션 생성 실패");
      }
      recSeq = 0;

      isRecordingAudio = true;
      recordBtn.classList.add("recording");
      recordBtn.setAttribute("aria-pressed", "true");
      recordBtn.setAttribute("aria-label", "음성 녹음 중지");

      console.log("🎙️ 녹음 시작");
      
      // ✅ 추가: 30초 후 자동 중지 타임아웃 설정
      recordingTimeout = setTimeout(() => {
        if (isRecordingAudio) {
          stopRecordingAudio("timeout-30s");
          console.log("⏱️ 녹음 시간 초과 (30초) - 자동 중지");
          addChatMessage("녹음 시간이 초과되었습니다. (최대 30초)", "system");
        }
      }, 30000); // 30초
    } catch (err) {
      console.error("녹음 시작 실패:", err);
      alert("녹음을 시작할 수 없습니다: " + err.message);
      stopRecordingAudio();
    }
  }

  // 녹음 종료/정리
  function stopRecordingAudio(reason) {
    console.log("🔚 녹음 중지:", reason || "");
    isRecordingAudio = false;

    if (workletNode) {
      try {
        workletNode.port.postMessage("stop");
      } catch (e) {}
      workletNode.port.onmessage = null;
      workletNode.disconnect();
      workletNode = null;
    }

    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
    }

    if (audioContext && audioContext.state !== "closed") {
      audioContext.close();
      audioContext = null;
    }

    recSessionId = null;
    recSeq = 0;
    
    // ✅ 추가: 타임아웃 정리
    if (recordingTimeout) {
      clearTimeout(recordingTimeout);
      recordingTimeout = null;
    }

    if (recordBtn) {
      recordBtn.classList.remove("recording");
      recordBtn.setAttribute("aria-pressed", "false");
      recordBtn.setAttribute("aria-label", "음성 녹음 시작");
    }
  }

  // 녹음 버튼 클릭 → 토글
  if (recordBtn) {
    recordBtn.addEventListener("click", () => {
      if (isRecordingAudio) {
        stopRecordingAudio("user-click");
      } else {
        startRecordingAudio();
      }
    });
  }

  // 페이지 이탈/숨김 시 녹음 중이면 정리
  window.addEventListener("beforeunload", () => {
    if (isRecordingAudio) {
      stopRecordingAudio("beforeunload");
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden && isRecordingAudio) {
      stopRecordingAudio("tab-hidden");
    }
  });
});