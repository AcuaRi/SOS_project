// followToggle.js

let followMe = false;

/**
 * 위치 따라가기 토글을 초기화하고, 지도 이동 기능을 반환합니다.
 * @param {L.Map} map - Leaflet 지도 객체
 * @param {Function} getMyLoc - 내 현재 위치를 반환하는 함수 (예: () => myLoc)
 * @returns {Function} updateMapFollow - 위치 변경 시 지도 중심 이동을 실행하는 함수
 */
export function setupFollowToggle(map, getMyLoc) {
  const toggle = document.getElementById("followToggle");

  // 토글 변경 이벤트 등록
  toggle.addEventListener("change", () => {
    followMe = toggle.checked;
    console.log("🧭 내 위치 따라가기:", followMe ? "ON" : "OFF");
  });

  // 외부에서 호출하여 지도 중심 이동 처리
  function updateMapFollow() {
    if (followMe && typeof getMyLoc === "function") {
      const myLoc = getMyLoc();
      if (myLoc && myLoc.lat && myLoc.lng) {
        map.setView([myLoc.lat, myLoc.lng], 15); // 줌은 필요에 따라 조정 가능
      }
    }
  }

  return updateMapFollow;
}
