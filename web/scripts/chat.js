const box  = document.getElementById("chat-log");   
const form = document.getElementById("chat-form");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(form);
  add("user", fd.get("symptom"));
  
  // 1) 위치 붙이기
  try {
    const pos = await new Promise(r =>
      navigator.geolocation.getCurrentPosition(p=>r(p), ()=>r(null))
    );
    if (pos) {
      fd.append("latitude",  pos.coords.latitude);
      fd.append("longitude", pos.coords.longitude);
    }
  } catch {}

  // 2) /analyze 호출
  const r1 = await fetch("/analyze", {method:"POST", body:fd});
  const j1 = await r1.json();          // {record_id, reply}
  
  // 3) /guide/{id} 호출
  const r2 = await fetch(`/guide/${j1.record_id}`);
  const j2 = await r2.json();          // {risk, dis, guide, lat, lng}
  
  add("bot", `🔴 위험도: ${j2.risk}\n💡 ${j2.guide}`);
  form.reset();
});

function add(who, txt){
  const div = document.createElement("div");
  div.className = who;
  div.textContent = txt;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}
