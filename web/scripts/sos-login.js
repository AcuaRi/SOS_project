document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const signupRedirectBtn = document.getElementById('signup-redirect-btn');

    if (loginForm) {
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            try {
                const response = await fetch('http://35.78.251.74:8000/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email, password }),
                });

                if (response.ok) {
                    window.location.href = 'http://35.78.251.74:8000/web/chat.html';
                } else {
                    const errorData = await response.json();
                    alert(`로그인 실패: ${errorData.detail || response.statusText}`);
                }
            } catch (error) {
                console.error('Error during login:', error);
                alert('로그인 중 오류가 발생했습니다.');
            }
        });
    }

    if (signupRedirectBtn) {
        signupRedirectBtn.addEventListener('click', () => {
            window.location.href = 'signup.html'; // 회원가입 페이지로 리다이렉트
        });
    }
});