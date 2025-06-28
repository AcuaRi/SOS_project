// 회원가입 JS

// Firebase 설정
const firebaseConfig = {
    apiKey: "AIzaSyBqSDsXEUs7AqOsgwf4SduC7g_evFvw6i8",
    authDomain: "emergencyapp-bd348.firebaseapp.com",
    databaseURL: "https://emergencyapp-bd348-default-rtdb.firebaseio.com",
    projectId: "emergencyapp-bd348",
    storageBucket: "emergencyapp-bd348.appspot.com",
    messagingSenderId: "794049403660",
    appId: "1:794049403660:web:cee8430aba611cf739c729",
    measurementId: "G-S23BY0GZFE"
  };
  
  firebase.initializeApp(firebaseConfig);
  const auth = firebase.auth();
  const database = firebase.database();
  
  // firebase 에서 (. # [ ] / )등의 기호는 쓰면 안됨 -> 전부 , 로 바꿔줌
  function encodeEmail(email) {
    return email.replace(/\./g, ',');
  }
  
  // 입력된 데이터 저장
  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('signUpButton').addEventListener('click', function () {
      const email = document.getElementById('signUpEmail').value;
      const password = document.getElementById('signUpPassword').value;
      const name = document.getElementById('realName').value;
      const phone = document.getElementById('phoneNumber').value;
      
      // 모든 칸 작성
      if (!email || !name || !password || !phone) {
        alert("모든 입력값을 올바르게 입력해 주세요.");
        return;
      }
      
      // Firebase DB에 토큰 별로 구분, 하위 폴더에 이름과 전호번호 저장
      auth.createUserWithEmailAndPassword(email, password)
        .then((userCredential) => {
            const uid = userCredential.user.uid;
            const userData = {
            name: name,
            phone: phone
            };
            return database.ref('users/' + uid).set(userData);
        })


        .then(() => {
          alert("회원가입 성공!");
        })

        .catch((error) => {
          console.error("오류:", error);
          alert("에러 발생: " + error.message);
        });
    });
  });
  