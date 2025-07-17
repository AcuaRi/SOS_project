document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.getElementById('signup-form');
    const loginRedirectBtn = document.getElementById('login-redirect-btn');

    if (signupForm) {
        signupForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            try {
                const response = await fetch('/auth/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email, password }),
                });

                if (response.ok) {
                    alert('회원가입 성공! 로그인 페이지로 이동합니다.');
                    window.location.href = 'sos-login.html'; // 로그인 페이지로 리다이렉트
                } else {
                    const errorData = await response.json();
                    alert(`회원가입 실패: ${errorData.detail || response.statusText}`);
                }
            } catch (error) {
                console.error('Error during signup:', error);
                alert('회원가입 중 오류가 발생했습니다.');
            }
        });
    }

    if (loginRedirectBtn) {
        loginRedirectBtn.addEventListener('click', () => {
            window.location.href = 'sos-login.html'; // 로그인 페이지로 리다이렉트
        });
    }
});