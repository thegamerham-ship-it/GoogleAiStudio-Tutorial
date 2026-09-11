    // 상태 변수
    let ytPlayer = null;
    let isPlayerReady = false;
    let currentVideoData = null;
    let timeUpdateInterval = null;

    // DOM 요소
    const urlInput = document.getElementById('url-input');
    const searchForm = document.getElementById('search-form');
    const searchBtn = document.getElementById('search-btn');
    const clearBtn = document.getElementById('clear-btn');
    const playerPlaceholder = document.getElementById('player-placeholder');

    const ctrlPlayPause = document.getElementById('ctrl-play-pause');
    const ctrlRewind = document.getElementById('ctrl-rewind');
    const ctrlForward = document.getElementById('ctrl-forward');
    const ctrlMuteBtn = document.getElementById('ctrl-mute-btn');
    const ctrlVolIcon = document.getElementById('ctrl-vol-icon');
    const ctrlVolumeSlider = document.getElementById('ctrl-volume-slider');
    const ctrlVolumeLabel = document.getElementById('ctrl-volume-label');
    const videoTimeDisplay = document.getElementById('video-time-display');

    const videoInfoCard = document.getElementById('video-info-card');
    const videoTitle = document.getElementById('video-title');
    const videoChannel = document.getElementById('video-channel');
    const videoDuration = document.getElementById('video-duration');
    const quickTagBar = document.getElementById('quick-tag-bar');
    const quickTagsContainer = document.getElementById('quick-tags-container');

    const tabChatBtn = document.getElementById('tab-chat-btn');
    const tabEntitiesBtn = document.getElementById('tab-entities-btn');
    const tabTranscriptBtn = document.getElementById('tab-transcript-btn');

    const tabChatContent = document.getElementById('tab-chat-content');
    const tabEntitiesContent = document.getElementById('tab-entities-content');
    const tabTranscriptContent = document.getElementById('tab-transcript-content');

    const aiLoading = document.getElementById('ai-loading');
    const aiLoadingText = document.getElementById('ai-loading-text');
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');

    const entitiesList = document.getElementById('entities-list');
    const entitiesCount = document.getElementById('entities-count');

    const transcriptList = document.getElementById('transcript-list');
    const transcriptCount = document.getElementById('transcript-count');
    const copyTranscriptBtn = document.getElementById('copy-transcript-btn');

    // YouTube IFrame API 준비 완료 콜백
    function onYouTubeIframeAPIReady() {
      console.log("[YouTube API] IFrame API Ready.");
    }

    // 유튜브 플레이어 초기화
    function initPlayer(videoId) {
      if (ytPlayer) {
        ytPlayer.loadVideoById(videoId);
        return;
      }

      ytPlayer = new YT.Player('yt-player', {
        videoId: videoId,
        playerVars: {
          autoplay: 1,
          controls: 1,
          modestbranding: 1,
          rel: 0,
        },
        events: {
          onReady: onPlayerReady,
          onStateChange: onPlayerStateChange
        }
      });
    }

    function onPlayerReady(event) {
      isPlayerReady = true;
      playerPlaceholder.classList.add('hidden');
      // 초기 볼륨 설정
      const vol = parseInt(ctrlVolumeSlider.value, 10) || 85;
      ytPlayer.setVolume(vol);

      // 주기적으로 현재 시간 동기화
      if (timeUpdateInterval) clearInterval(timeUpdateInterval);
      timeUpdateInterval = setInterval(updateCurrentTimeDisplay, 500);
    }

    function onPlayerStateChange(event) {
      if (event.data === YT.PlayerState.PLAYING) {
        ctrlPlayPause.innerHTML = '<i class="ph-fill ph-pause text-sm"></i>';
      } else {
        ctrlPlayPause.innerHTML = '<i class="ph-fill ph-play text-sm"></i>';
      }
    }

    function updateCurrentTimeDisplay() {
      if (!isPlayerReady || !ytPlayer || typeof ytPlayer.getCurrentTime !== 'function') return;
      const cur = Math.floor(ytPlayer.getCurrentTime() || 0);
      const total = Math.floor(ytPlayer.getDuration() || 0);
      videoTimeDisplay.textContent = `${formatTime(cur)} / ${formatTime(total)}`;
    }

    function formatTime(sec) {
      const m = Math.floor(sec / 60);
      const s = Math.floor(sec % 60);
      return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
    }

    // 특정 초로 이동 및 자동 재생 (Seek & Play)
    window.seekAndPlay = function(seconds) {
      if (!isPlayerReady || !ytPlayer) return;
      ytPlayer.seekTo(seconds, true);
      ytPlayer.playVideo();
    };

    // 컨트롤러 이벤트
    ctrlPlayPause.addEventListener('click', () => {
      if (!isPlayerReady || !ytPlayer) return;
      const state = ytPlayer.getPlayerState();
      if (state === YT.PlayerState.PLAYING) {
        ytPlayer.pauseVideo();
      } else {
        ytPlayer.playVideo();
      }
    });

    ctrlRewind.addEventListener('click', () => {
      if (!isPlayerReady || !ytPlayer) return;
      const cur = ytPlayer.getCurrentTime();
      ytPlayer.seekTo(Math.max(0, cur - 5), true);
    });

    ctrlForward.addEventListener('click', () => {
      if (!isPlayerReady || !ytPlayer) return;
      const cur = ytPlayer.getCurrentTime();
      ytPlayer.seekTo(cur + 5, true);
    });

    // 🔊 볼륨 조절 슬라이더
    ctrlVolumeSlider.addEventListener('input', (e) => {
      const vol = parseInt(e.target.value, 10);
      ctrlVolumeLabel.textContent = `${vol}%`;
      if (isPlayerReady && ytPlayer) {
        ytPlayer.setVolume(vol);
        if (vol === 0) {
          ytPlayer.mute();
          ctrlVolIcon.className = "ph-bold ph-speaker-slash text-lg text-[#D95338]";
        } else {
          ytPlayer.unMute();
          ctrlVolIcon.className = vol > 50 ? "ph-bold ph-speaker-high text-lg text-[#5C5346]" : "ph-bold ph-speaker-low text-lg text-[#5C5346]";
        }
      }
    });

    ctrlMuteBtn.addEventListener('click', () => {
      if (!isPlayerReady || !ytPlayer) return;
      if (ytPlayer.isMuted()) {
        ytPlayer.unMute();
        const vol = parseInt(ctrlVolumeSlider.value, 10) || 85;
        ytPlayer.setVolume(vol);
        ctrlVolIcon.className = "ph-bold ph-speaker-high text-lg text-[#5C5346]";
      } else {
        ytPlayer.mute();
        ctrlVolIcon.className = "ph-bold ph-speaker-slash text-lg text-[#D95338]";
      }
    });

    // 검색창 입력 이벤트
    urlInput.addEventListener('input', () => {
      clearBtn.classList.toggle('hidden', !urlInput.value);
    });
    clearBtn.addEventListener('click', () => {
      urlInput.value = '';
      clearBtn.classList.add('hidden');
      urlInput.focus();
    });

    // 검색 제출: 오디오 다운로드 & Gemini 분석 처리
    searchForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const url = urlInput.value.trim();
      if (!url) return;

      searchBtn.disabled = true;
      searchBtn.classList.add('opacity-50');
      aiLoading.classList.remove('hidden');
      aiLoadingText.textContent = "오디오 분석 및 Gemini 핵심 색인 & 타임스탬프 추출 중...";

      try {
        const res = await fetch('/api/process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url })
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: '처리 실패' }));
          throw new Error(err.detail || '영상 처리에 실패했습니다.');
        }

        const data = await res.json();
        currentVideoData = data;

        // 플레이어에 영상 로드
        initPlayer(data.video_id);

        // 메타데이터 렌더링
        videoTitle.textContent = data.title;
        videoChannel.textContent = data.channel;
        videoDuration.textContent = formatTime(data.duration);
        videoInfoCard.classList.remove('hidden');

        // 1. 핵심 색인 목록 렌더링
        renderEntities(data.entities);

        // 2. 주요 구간 빠른 이동 태그 칩스 렌더링
        renderQuickTags(data.entities, data.segments);

        // 3. 전체 자막 렌더링
        renderTranscripts(data.segments);

        // 채팅 입력창 활성화
        chatInput.disabled = false;
        chatSendBtn.disabled = false;
        chatInput.placeholder = `'${data.title}'에 대해 질문하세요...`;

        // 완료 안내 메시지 추가 (캐시 여부 분기)
        if (data.from_cache) {
          appendAIMessage(`⚡ **[CSV 캐시 로딩]** 이전에 분석하여 저장된 영상입니다!\n\nGemini 재호출 없이 **CSV 파일(transcripts_cache.csv)**에서 **${data.entities?.length || 0}개 핵심 색인** 및 **${data.segments.length}개 자막**을 즉시 불러왔습니다.\n\n궁금한 점이나 찾고 싶은 장면을 바로 질문해보세요!`);
        } else {
          appendAIMessage(`✅ **${data.title}** 신규 분석 완료!\n\n총 **${data.entities?.length || 0}개 핵심 색인**과 **${data.segments.length}개**의 타임스탬프 자막이 추출되어 **CSV 파일(transcripts_cache.csv)**에 저장되었습니다.\n\n다음 번에 동일한 링크를 입력하시면 대기 시간 없이 즉시 불러옵니다!`);
        }

      } catch (err) {
        alert(err.message);
      } finally {
        aiLoading.classList.add('hidden');
        searchBtn.disabled = false;
        searchBtn.classList.remove('opacity-50');
      }
    });

    // 1. 핵심 색인 목록(Entities/Chapters) 렌더링
    function renderEntities(entities) {
      entitiesList.innerHTML = '';
      if (!entities || entities.length === 0) {
        entitiesCount.textContent = '0개 색인 항목';
        entitiesList.innerHTML = `
          <div class="p-8 text-center text-[#7D7568] text-xs">
            <i class="ph-bold ph-info text-2xl text-[#A39B8E] mb-2 block"></i>
            <p class="font-medium text-[#4A4337]">감지된 별도 소주제 색인이 없습니다.</p>
            <p class="text-[11px] text-[#7D7568] mt-1">우측 '타임라인 자막' 탭에서 시간대별 상세 대사를 확인하세요.</p>
          </div>
        `;
        return;
      }

      entitiesCount.textContent = `${entities.length}개 색인 항목`;

      entities.forEach((item) => {
        const card = document.createElement('div');
        card.className = "group p-3.5 bg-white hover:bg-[#FDFBF7] rounded-xl border border-[#E8E1D4] hover:border-[#D95338]/50 cursor-pointer transition flex items-start gap-3 shadow-xs";
        card.onclick = () => seekAndPlay(item.seconds || 0);

        card.innerHTML = `
          <button class="shrink-0 px-2.5 py-1 bg-[#FDF1EC] group-hover:bg-[#D95338] text-[#D95338] group-hover:text-white rounded-lg text-xs font-mono font-bold flex items-center gap-1 transition">
            <span>${item.time_str || '00:00'}</span>
            <i class="ph-fill ph-play text-[10px]"></i>
          </button>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <h4 class="text-xs font-bold text-[#1C2E24] group-hover:text-[#D95338] transition truncate">${escapeHtml(item.title || '주제')}</h4>
            </div>
            <p class="text-[11px] text-[#6E665A] leading-relaxed">${escapeHtml(item.summary || '')}</p>
          </div>
        `;
        entitiesList.appendChild(card);
      });
    }

    // 2. 주요 구간 빠른 이동 태그(Chips) 렌더링
    function renderQuickTags(entities, segments) {
      quickTagsContainer.innerHTML = '';
      
      const tags = (entities && entities.length > 0) 
        ? entities 
        : (segments || []).slice(0, 6).map(s => ({
            time_str: s.timestamp,
            seconds: s.start_seconds,
            title: s.text.length > 15 ? s.text.slice(0, 15) + '...' : s.text
          }));

      if (!tags || tags.length === 0) {
        quickTagBar.classList.add('hidden');
        return;
      }

      quickTagBar.classList.remove('hidden');

      tags.forEach(t => {
        const chip = document.createElement('button');
        chip.className = "px-2.5 py-1 bg-[#FDF1EC] hover:bg-[#FAE4DC] border border-[#F6D9CE] rounded-lg text-xs text-[#D95338] hover:text-[#C8482E] whitespace-nowrap transition flex items-center gap-1.5 font-mono shrink-0 shadow-2xs";
        chip.onclick = () => seekAndPlay(t.seconds || 0);
        chip.innerHTML = `
          <span class="font-bold">#${t.time_str || '00:00'}</span>
          <span class="text-[#4A4337] font-sans">${escapeHtml(t.title || '')}</span>
        `;
        quickTagsContainer.appendChild(chip);
      });
    }

    // 3. 전체 자막 목록 렌더링
    function renderTranscripts(segments) {
      transcriptList.innerHTML = '';
      transcriptCount.textContent = `${segments.length}개 자막 문장`;

      if (!segments || segments.length === 0) {
        transcriptList.innerHTML = '<div class="text-center py-8 text-xs text-[#7D7568]">추출된 자막이 없습니다.</div>';
        return;
      }

      segments.forEach((s) => {
        const item = document.createElement('div');
        item.className = "p-2.5 rounded-lg bg-white hover:bg-[#FDFBF7] transition border border-[#E8E1D4] flex items-start gap-3 cursor-pointer group shadow-xs";
        item.onclick = () => seekAndPlay(s.start_seconds);

        item.innerHTML = `
          <button class="px-2 py-0.5 rounded bg-[#FDF1EC] text-[#D95338] group-hover:bg-[#D95338] group-hover:text-white text-[11px] font-mono font-bold transition whitespace-nowrap">
            ${s.timestamp} ▶
          </button>
          <div class="flex-1 text-xs">
            <span class="font-semibold text-[#7D7568] text-[10px] mr-1">[${s.speaker}]</span>
            <span class="text-[#2E2B27]">${s.text}</span>
          </div>
        `;
        transcriptList.appendChild(item);
      });
    }

    // 3-way 탭 전환 이벤트
    function switchTab(activeTab) {
      const tabs = [
        { name: 'chat', btn: tabChatBtn, content: tabChatContent },
        { name: 'entities', btn: tabEntitiesBtn, content: tabEntitiesContent },
        { name: 'transcript', btn: tabTranscriptBtn, content: tabTranscriptContent }
      ];
      tabs.forEach(t => {
        if (t.name === activeTab) {
          t.btn.className = "flex-1 py-3 text-xs font-bold text-[#1C2E24] bg-white border-b-2 border-[#234B3D] flex items-center justify-center gap-1.5 transition";
          t.content.classList.remove('hidden');
        } else {
          t.btn.className = "flex-1 py-3 text-xs font-medium text-[#7D7568] hover:text-[#1C2E24] bg-transparent flex items-center justify-center gap-1.5 transition border-b-2 border-transparent";
          t.content.classList.add('hidden');
        }
      });
    }

    tabChatBtn.addEventListener('click', () => switchTab('chat'));
    tabEntitiesBtn.addEventListener('click', () => switchTab('entities'));
    tabTranscriptBtn.addEventListener('click', () => switchTab('transcript'));

    // 채팅 전송 (Gemini 3.8 Flash 질의응답)
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const q = chatInput.value.trim();
      if (!q || !currentVideoData) return;

      appendUserMessage(q);
      chatInput.value = '';
      chatInput.disabled = true;
      chatSendBtn.disabled = true;

      // 타이핑 로딩 표시
      const loadingBubble = appendLoadingBubble();

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: q,
            video_id: currentVideoData.video_id,
            transcript_summary: currentVideoData.full_text,
            segments: currentVideoData.segments,
            entities: currentVideoData.entities || []
          })
        });

        if (!res.ok) throw new Error('답변 생성 실패');
        const data = await res.json();

        loadingBubble.remove();
        appendAIMessage(data.answer, data.timestamps);

      } catch (err) {
        loadingBubble.remove();
        appendAIMessage(`⚠️ 오류가 발생했습니다: ${err.message}`);
      } finally {
        chatInput.disabled = false;
        chatSendBtn.disabled = false;
        chatInput.focus();
      }
    });

    // 추천 질문 클릭
    document.querySelectorAll('.chip').forEach(btn => {
      btn.addEventListener('click', () => {
        if (!currentVideoData) {
          alert('먼저 상단에서 유튜브 영상을 검색해주세요!');
          return;
        }
        chatInput.value = btn.textContent.replace(/[📌⏱️🔍📋⭐]/g, '').trim();
        chatForm.dispatchEvent(new Event('submit'));
      });
    });

    function appendUserMessage(text) {
      const bubble = document.createElement('div');
      bubble.className = "flex justify-end";
      bubble.innerHTML = `
        <div class="bg-[#234B3D] text-white rounded-2xl rounded-tr-none px-4 py-2.5 max-w-[85%] text-xs shadow-sm leading-relaxed">
          ${escapeHtml(text)}
        </div>
      `;
      chatMessages.appendChild(bubble);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendAIMessage(markdownText, timestamps = []) {
      const bubble = document.createElement('div');
      bubble.className = "flex justify-start gap-2.5 items-start";

      // 타임스탬프 문자열 [MM:SS] 또는 MM:SS를 클릭 가능한 버튼으로 치환
      let parsedHtml = marked.parse(markdownText);
      parsedHtml = parsedHtml.replace(/\[?(\d{1,2}:\d{2})\]?/g, (match, p1) => {
        const parts = p1.split(':');
        const secs = parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
        return `<button onclick="seekAndPlay(${secs})" class="inline-flex items-center gap-1 px-2 py-0.5 mx-0.5 rounded bg-[#FDF1EC] hover:bg-[#D95338] text-[#D95338] hover:text-white font-mono text-[11px] font-bold transition shadow-2xs">▶ ${p1}</button>`;
      });

      bubble.innerHTML = `
        <div class="w-6 h-6 rounded-lg bg-[#234B3D] flex items-center justify-center text-white text-xs shrink-0 mt-0.5 shadow-xs">
          <i class="ph-bold ph-sparkle text-xs"></i>
        </div>
        <div class="bg-white text-[#2E2B27] border border-[#E8E1D4] rounded-2xl rounded-tl-none p-3.5 max-w-[90%] text-xs markdown-body shadow-xs">
          ${parsedHtml}
        </div>
      `;
      chatMessages.appendChild(bubble);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendLoadingBubble() {
      const bubble = document.createElement('div');
      bubble.className = "flex justify-start gap-2.5 items-center";
      bubble.innerHTML = `
        <div class="w-6 h-6 rounded-lg bg-[#234B3D] flex items-center justify-center text-white text-xs shrink-0 shadow-xs">
          <i class="ph-bold ph-sparkle text-xs"></i>
        </div>
        <div class="bg-white border border-[#E8E1D4] rounded-2xl rounded-tl-none px-4 py-2.5 text-xs text-[#7D7568] flex items-center gap-2 shadow-xs">
          <div class="w-3 h-3 border-2 border-[#C8BFB0] border-t-[#D95338] rounded-full animate-spin"></div>
          <span>Gemini 3.8 Flash 답변 작성 중...</span>
        </div>
      `;
      chatMessages.appendChild(bubble);
      chatMessages.scrollTop = chatMessages.scrollHeight;
      return bubble;
    }

    function escapeHtml(str) {
      return str.replace(/[&<>'"]/g, 
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
      );
    }

    // 전문 복사
    copyTranscriptBtn.addEventListener('click', async () => {
      if (!currentVideoData || !currentVideoData.full_text) return;
      try {
        await navigator.clipboard.writeText(currentVideoData.full_text);
        copyTranscriptBtn.innerHTML = '<i class="ph-bold ph-check text-[#4C7A5D]"></i><span>복사 완료!</span>';
        setTimeout(() => {
          copyTranscriptBtn.innerHTML = '<i class="ph-bold ph-copy"></i><span>전문 복사</span>';
        }, 2000);
      } catch (err) {
        alert('복사 실패');
      }
    });
