// button.html의 JS

document.addEventListener('DOMContentLoaded', () => {
  // id가 "button"인 요소를 찾음
  const button = document.getElementById("button");
  if (!button) return;

  button.addEventListener("click", () => {
    // 버튼이 loading 클래스라면 클릭 무시 (연속 클릭 방지)
    if (button.classList.contains("loading")) return;

    // clickButton 이라는 함수가 정의되어 있으면 실행
    if (typeof clickButton === "function") clickButton();
    
    // 3.7초 후 새탭으로 "/test1" 페이지 열기
    setTimeout(() => window.open("/test1", "_blank"), 3700);
  });
});
