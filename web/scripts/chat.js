document.addEventListener("DOMContentLoaded", () => {
  console.log("\ud83d\udce6 DOM \ub85c\ub4dc \uc644\ub8cc");
  

  document.getElementById("hospital-btn").addEventListener("click", () => {
    //window.location.href = "/hospital/user-map-new";
    //console.log("hospital");
    window.location.href = "/web/hospital.html";
  });

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      console.log("\ud83d\udccd \uc704\uce58 \uc815\ubcf4:", lat, lng);
      document.getElementById("latitude").value = lat;
      document.getElementById("longitude").value = lng;

      fetch(`${window.location.origin}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ latitude: lat, longitude: lng })
      });
    },
    (err) => console.error("\u274c \uc704\uce58 \ucd94\uc138 \uc2e4\ud328:", err)
  );

  const form = document.getElementById("chat-form");
  const chatLog = document.getElementById("chat-log");
  const symptomInput = document.getElementById("symptom-input");
  const imageInput = document.getElementById("image-upload");
  const previewContainer = document.getElementById("preview-container");

  function scrollToBottom() {
    chatLog.lastElementChild?.scrollIntoView({ behavior: "smooth" });
  }

  function appendUserBubble(message, imageFile = null) {
    console.log("\ud83d\udcac \uc0ac\uc6a9\uc790 \uc785\ub825:", message);
    let imageTag = "";
    if (imageFile) {
      const imageURL = URL.createObjectURL(imageFile);
      imageTag = `<img src="${imageURL}" class="uploaded-image" alt="\uc5c5\ub85c\ub4dc \uc774\ubbf8\uc9c0">`;
      console.log("\ud83d\uddbc\ufe0f \uc774\ubbf8\uc9c0 \uc5c5\ub85c\ub4dc\ub428:", imageFile.name);
    }

    chatLog.insertAdjacentHTML("beforeend", `
      <div class="chat-bubble user">
        <div class="message">
          ${message}<br>
          ${imageTag}
        </div>
        <img src="/static/Symptoms_icon.png" class="icon" alt="User">
      </div>
    `);

    scrollToBottom();
  }

  function showLoadingBubble() {
    const loadingMessage = document.createElement("div");
    loadingMessage.className = "chat-bubble bot";
    loadingMessage.id = "loading-bubble";
    loadingMessage.innerHTML = `
      <img src="/static/Chatbot_icon.png" class="icon" alt="Bot">
      <div class="message loading">\ubd84\uc11d \uc911\uc785\ub2c8\ub2e4...</div>
    `;
    chatLog.appendChild(loadingMessage);
    scrollToBottom();
  }

  function removeLoadingBubble() {
    document.getElementById("loading-bubble")?.remove();
  }

  function showBotReply(replyText) {
    chatLog.insertAdjacentHTML("beforeend", `
      <div class="chat-bubble bot">
        <img src="/static/Chatbot_icon.png" class="icon" alt="Bot">
        <div class="message">${replyText.replace(/\n/g, "<br>")}</div>
      </div>
    `);
    scrollToBottom();
  }

  async function sendToAnalyze(finalSymptom, imageFile = null) {
    const analyzeForm = new FormData(form);
    analyzeForm.set("symptom", finalSymptom);
    if (imageFile) {
      analyzeForm.set("image", imageFile);
    }

    try {
      const analyzeRes = await fetch("/analyze", {
        method: "POST",
        body: analyzeForm
      });
      const analyzeResult = await analyzeRes.json();

      if (!analyzeResult.record_id) {
        throw new Error("record_id\ub97c \ubc1b\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.");
      }

      const guideRes = await fetch(`/guide/${analyzeResult.record_id}`);
      const guideResult = await guideRes.json();

      removeLoadingBubble();
      showBotReply(guideResult.guide);
    } catch (err) {
      console.error("\u274c \ubd84\uc11d \ub610\ub294 \uac00\uc774\ub4dc \uc694\uccad \uc2e4\ud328:", err);
      removeLoadingBubble();
      showBotReply("\uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4. \uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc \uc2dc\ub3c4\ud574\uc8fc\uc138\uc694.");
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const symptomText = symptomInput.value.trim();
    const audio = document.getElementById("audio-upload").files[0];
    const imageFile = imageInput && imageInput.files.length > 0 ? imageInput.files[0] : null;

    if (symptomText.length > 0) {
      appendUserBubble(symptomText, imageFile);
      showLoadingBubble();
      await sendToAnalyze(symptomText, imageFile);
      symptomInput.value = "";
      imageInput.value = "";
      previewContainer.innerHTML = "";
      previewContainer.style.display = "none";
    } else if (audio && audio.size > 0) {
      const sttForm = new FormData();
      sttForm.append("audio", audio);

      try {
        const sttRes = await fetch("/analyze/stt", {
          method: "POST",
          body: sttForm
        });

        const sttResult = await sttRes.json();
        const sttText = sttResult.stt_text?.trim();
        if (!sttText) return;

        appendUserBubble(sttText, imageFile);
        showLoadingBubble();
        await sendToAnalyze(sttText, imageFile);
        symptomInput.value = "";
        imageInput.value = "";
        previewContainer.innerHTML = "";
        previewContainer.style.display = "none";
      } catch (err) {
        console.error("\u274c STT \uc694\uccad \uc2e4\ud328:", err);
      }
    }
  });

  imageInput.addEventListener("change", () => {
    previewContainer.innerHTML = "";
    const file = imageInput.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      previewContainer.innerHTML = `
        <img src="${reader.result}" class="preview-img" alt="\ubbf8\ub9ac\ubcf4\uae30">
        <button class="remove-preview">\u2716</button>
      `;
      previewContainer.style.display = "flex";

      previewContainer.querySelector(".remove-preview").addEventListener("click", () => {
        imageInput.value = "";
        previewContainer.innerHTML = "";
        previewContainer.style.display = "none";
      });
    };
    reader.readAsDataURL(file);
  });

  let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;

  document.getElementById("record-toggle").addEventListener("click", async () => {
    const button = document.getElementById("record-toggle");
    try {
      if (!isRecording) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);

        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
          const file = new File([audioBlob], "recorded_audio.webm", { type: "audio/webm" });
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(file);
          document.getElementById("audio-upload").files = dataTransfer.files;

          symptomInput.value = "";
          form.dispatchEvent(new Event("submit", { cancelable: true }));
        };

        mediaRecorder.start();
        isRecording = true;
        button.textContent = "\ud83d\udd34";
      } else {
        mediaRecorder.stop();
        isRecording = false;
        button.textContent = "\ud83c\udf99\ufe0f";
      }
    } catch (err) {
      console.error("\u274c \ub9c8\uc774\ud06c \uc811\uadfc \uc2e4\ud328:", err);
    }
  });
});

// // sos ��ư ����
// document.getElementById("sos-btn").addEventListener("click", async () => {
//   // ��ġ �޾ƿ���
//   navigator.geolocation.getCurrentPosition(async (position) => {
//     const lat = position.coords.latitude;
//     const lng = position.coords.longitude;
//     const stored = sessionStorage.getItem('IdData');
//     //const jwt = localStorage.getItem("jwt_token");  // �α��� �� ����� ��ū

//     // ������ ��ġ ����
//     console.log(JSON.stringify({stored, lat, lng }))
//     const res = await fetch("/navition/location", {
//       method: "POST",
//       headers: {
//        // "Authorization": "Bearer " + jwt,
//         "Content-Type": "application/json"
//       },
//       body: JSON.stringify({stored, lat, lng })

//     });

//     const data = await res.json();
//     if (data.success) {
//       // ������ index1.html���� �̵�
//       window.location.href = "/web/index1.html";
//     } else {
//       alert("��ġ ���� ����: " + (data.msg || ""));
//     }
//   }, (err) => {
//     alert("��ġ ������ ������ �� �����ϴ�: " + err.message);
//   });
// });

// // ��ȣ�� �Ÿ� ��ư ����
// document.getElementById("notification-btn").addEventListener("click", () => {
//   window.location.href = "/web/notification.html";
// });

// document.addEventListener("DOMContentLoaded", () => {
//   console.log("?�� DOM 로딩 ?�료");

//   navigator.geolocation.getCurrentPosition(
//     (position) => {
//       const lat = position.coords.latitude;
//       const lng = position.coords.longitude;

//       console.log("?�� ?�치 ?�보:", lat, lng);
//       document.getElementById("latitude").value = lat;
//       document.getElementById("longitude").value = lng;

//       // ?��?�??�마 진철??기능?�랑 ?�결?�는 부분인거같?�?�맞??
//       fetch(`${window.location.origin}/analyze`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ latitude: lat, longitude: lng })
//       });
//     },
//     (err) => console.error("???�치 추적 ?�패:", err)
//   );

//   document.getElementById("chat-form").addEventListener("submit", async (e) => {
//     e.preventDefault();
//     console.log("?�� 채팅 ???�출 감�?");

//     const form = e.target;
//     const chatLog = document.getElementById("chat-log");

//     const symptomInput = document.getElementById("symptom-input");
//     const symptomText = symptomInput.value.trim();
//     const audio = document.getElementById("audio-upload").files[0];
//     const imageInput = document.getElementById("image-upload");
//     const imageFile = imageInput && imageInput.files.length > 0 ? imageInput.files[0] : null;

//     function appendUserBubble(message, imageFile = null) {
//       console.log("?�� ?�용???�력:", message);
//       let imageTag = "";
//       if (imageFile) {
//         const imageURL = URL.createObjectURL(imageFile);
//         imageTag = `<img src="${imageURL}" class="uploaded-image" alt="?�로???��?지">`;
//         console.log("?���??��?지 ?�로?�됨:", imageFile.name);
//       }

//       chatLog.insertAdjacentHTML("beforeend", `
//         <div class="chat-bubble user">
//           <div class="message">
//             ${message}<br>
//             ${imageTag}
//           </div>
//           <img src="/static/Symptoms_icon.png" class="icon" alt="User">
//         </div>
//       `);
//     }

//     function showLoadingBubble() {
//       console.log("??분석 �?메시지 ?�시");
//       const loadingMessage = document.createElement("div");
//       loadingMessage.className = "chat-bubble bot";
//       loadingMessage.id = "loading-bubble";
//       loadingMessage.innerHTML = `
//         <img src="/static/Chatbot_icon.png" class="icon" alt="Bot">
//         <div class="message loading">분석 중입?�다...</div>
//       `;
//       chatLog.appendChild(loadingMessage);
//     }

//     function removeLoadingBubble() {
//       console.log("?�� 로딩 메시지 ?�거");
//       document.getElementById("loading-bubble")?.remove();
//     }

//     function showBotReply(replyText) {
//       console.log("?�� ?�버 ?�답 ?�시:", replyText);
//       chatLog.insertAdjacentHTML("beforeend", `
//         <div class="chat-bubble bot">
//           <img src="/static/Chatbot_icon.png" class="icon" alt="Bot">
//           <div class="message">${replyText.replace(/\n/g, "<br>")}</div>
//         </div>
//       `);
//     }

//     async function sendToAnalyze(finalSymptom, imageFile = null) {
//       console.log("?�� 분석 ?�송 ?�작:", finalSymptom);
//       const analyzeForm = new FormData(form);
//       analyzeForm.set("symptom", finalSymptom);

//       if (imageFile) {
//         analyzeForm.set("image", imageFile);
//       }

//       try {
//         // 1. 증상 분석 ?�청
//         const analyzeRes = await fetch("/analyze", {
//           method: "POST",
//           body: analyzeForm
//         });
//         const analyzeResult = await analyzeRes.json();
//         console.log("?�� 분석 ?�답 ?�신:", analyzeResult);

//         if (!analyzeResult.record_id) {
//           throw new Error("record_id�?받�? 못했?�니??");
//         }

//         // 2. ?�세 가?�드 ?�청
//         const guideRes = await fetch(`/guide/${analyzeResult.record_id}`);
//         const guideResult = await guideRes.json();
//         console.log("?�� 가?�드 ?�답 ?�신:", guideResult);

//         removeLoadingBubble();
//         showBotReply(guideResult.guide); // ?�세 가?�드�??�면???�시

//       } catch (err) {
//         console.error("??분석 ?�는 가?�드 ?�청 ?�패:", err);
//         removeLoadingBubble();
//         showBotReply("?�류가 발생?�습?�다. ?�시 ???�시 ?�도?�주?�요.");
//       }
//     }

//     if (symptomText.length > 0) {
//       appendUserBubble(symptomText, imageFile);
//       showLoadingBubble();
//       await sendToAnalyze(symptomText, imageFile);
//       symptomInput.value = "";
//     } else if (audio && audio.size > 0) {
//       console.log("?�� ?�디???�일 존재, STT ?�송 ?�작");
//       const sttForm = new FormData();
//       sttForm.append("audio", audio);

//       try {
//         const sttRes = await fetch("/analyze/stt", {   // ??prefix 반영
//           method: "POST",
//           body: sttForm
//         });

//         const sttResult = await sttRes.json();
//         console.log("?�� STT ?�답:", sttResult);

//         const sttText = sttResult.stt_text?.trim();
//         if (!sttText) {
//           console.warn("?�️ STT 결과 ?�음");
//           return;
//         }

//         appendUserBubble(sttText, imageFile);
//         showLoadingBubble();
//         await sendToAnalyze(sttText, imageFile);
//       } catch (err) {
//         console.error("??STT ?�청 ?�패:", err);
//       }
//     }
//   });
//     const imageInput = document.getElementById("image-upload");
//   const previewContainer = document.getElementById("preview-container");

//   imageInput.addEventListener("change", () => {
//     previewContainer.innerHTML = "";
//     const file = imageInput.files[0];
//     if (!file) return;

//     const reader = new FileReader();
//     reader.onload = () => {
//       previewContainer.innerHTML = `
//         <img src="${reader.result}" class="preview-img" alt="미리보기">
//         <button class="remove-preview">??/button>
//       `;
//       previewContainer.style.display = "flex";

//       previewContainer.querySelector(".remove-preview").addEventListener("click", () => {
//         imageInput.value = "";
//         previewContainer.innerHTML = "";
//         previewContainer.style.display = "none";
//       });
//     };
//     reader.readAsDataURL(file);
//   });


//   // ?�성 ?�음 처리
//   let mediaRecorder;
//   let audioChunks = [];
//   let isRecording = false;

//   document.getElementById("record-toggle").addEventListener("click", async () => {
//     const button = document.getElementById("record-toggle");
//     console.log("?���??�음 버튼 ?�릭??);

//     try {
//       if (!isRecording) {
//         console.log("?�� ?�음 ?�작 ?�도");
//         const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
//         console.log("??마이???�트�??�근 ?�공");

//         mediaRecorder = new MediaRecorder(stream);
//         audioChunks = [];

//         mediaRecorder.ondataavailable = event => {
//           console.log("?�� ?�디??조각 ?�신");
//           audioChunks.push(event.data);
//         };

//         mediaRecorder.onstop = () => {
//           console.log("?�� ?�음 종료, Blob ?�성");
//           const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
//           const file = new File([audioBlob], "recorded_audio.webm", { type: "audio/webm" });

//           const dataTransfer = new DataTransfer();
//           dataTransfer.items.add(file);

//           document.getElementById("audio-upload").files = dataTransfer.files;
//           console.log("?�� ?�음???�일 ?�???�료:", file);

//           document.getElementById("symptom-input").value = "";
//           document.getElementById("chat-form").dispatchEvent(new Event("submit", { cancelable: true }));
//         };

//         mediaRecorder.onerror = e => {
//           console.error("???�음 �??�류 발생:", e);
//         };

//         mediaRecorder.start();
//         isRecording = true;
//         button.textContent = "?��";
//         console.log("?�️ ?�음 ?�작??);
//       } else {
//         mediaRecorder.stop();
//         isRecording = false;
//         button.textContent = "?��";
//         console.log("?�️ ?�음 ?��???);
//       }
//     } catch (err) {
//       console.error("??마이???�근 ?�패:", err);
//     }
//   });
// });



