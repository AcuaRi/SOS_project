// // sos ��ư ����
document.getElementById("sos-btn").addEventListener("click", async () => {
  //console.log("abc")
//   // ��ġ �޾ƿ���
  
  const lat = 35.65525241124183;//position.coords.latitude;
  const lng = 139.76066445459867;//position.coords.longitude;
  const email = sessionStorage.getItem('IdData');
    //const jwt = localStorage.getItem("jwt_token");  // �α��� �� ����� ��ū

//     // ������ ��ġ ����
  //console.log(JSON.stringify({stored, lat, lng }))
  const res = await fetch("/navigation/sos_location", {
    method: "POST",
    headers: {
     // "Authorization": "Bearer " + jwt,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({email, lat, lng })
  });

  const data = await res.json();
  if (data.success) {
    // ������ index1.html���� �̵�
    window.location.href = "/web/index1.html";
  } else {
    alert("1번: " + (data.msg || ""));
  }
}, (err) => {
  alert("2번: " + err.message);
  
});

// ��ȣ�� �Ÿ� ��ư ����
document.getElementById("notification-btn").addEventListener("click", () => {
  window.location.href = "/web/notification.html";
});

document.getElementById("guardian-add-btn").addEventListener("click", () => {
  const data = sessionStorage.getItem('IdData');
  sessionStorage.setItem('IdData', JSON.stringify(data));
  //alert(data);

  window.location.href = "/web/add_friend.html";
});
