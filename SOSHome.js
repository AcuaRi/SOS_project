import React from 'react';
import './SOS.css';
import pancakes from 'images/pancakes.png';

function SOS() {
  return (
    <div className="sos-container">
      <img src={pancakes} alt="AI 응급 대응 로고" className="sos-logo" />
      <h2 className="sos-title">AI 응급 대응 도우미</h2>

      <input type="text" placeholder="Username" className="sos-input" />
      <input type="password" placeholder="Password" className="sos-input" />

      <div className="sos-button-group">
        <button className="sos-login">로그인</button>
        <button className="sos-register">계정 만들기</button>
      </div>

      <div className="sos-social-buttons">
        <button className="sos-social google">G</button>
        <button className="sos-social kakao">kakao</button>
        <button className="sos-social line">LINE</button>
      </div>

      <p className="sos-forgot">비밀번호를 잊으셨나요?</p>
    </div>
  );
}

export default SOS;
