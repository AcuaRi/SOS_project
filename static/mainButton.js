// 버튼 초기 설정
const button = document.getElementById('mainButton');
var disabled = false;

// 버튼 상태 전환
window.clickButton = function () {
  if (!disabled) {
    disabled = true;
    // 로딩 시작
    button.classList.add('loading');
    button.classList.remove('ready');
    // 로딩 종료 직전, 점 사라지는 애니메이션
    setTimeout(() => {
      button.classList.add('complete');
      button.classList.remove('loading');
      // 점이 완전히 사라진 뒤 success 등장
      setTimeout(() => {
        disabled = false;
        button.classList.add('ready');
        button.classList.remove('complete');
      }, 4000);
    }, 1800);
  }
};

// click button on spacebar or return keypress
document.body.onkeyup = (e) => {
  if (e.keyCode == 13 || e.keyCode == 32) {
    window.clickButton();
  }
};

const textElements = button.querySelectorAll('.button-text');
textElements.forEach((element) => {
  const characters = element.innerText.split('');
  let characterHTML = '';
  characters.forEach((letter, index) => {
    characterHTML += `<span class="char${index}" style="--d:${index * 30}ms; --dr:${(characters.length - index - 1) * 30}ms;">${letter}</span>`;
  });
  element.innerHTML = characterHTML;
});
