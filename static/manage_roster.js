function certs2HTML() {
    let certs = document.getElementById("certs-data-raw").value.toString().split("");
    if (certs.length == 1) {
        certs = [0, 0, 0, 0, 0, 0];
    }
    let htmls = [
        document.getElementById("del-cert"),
        document.getElementById("gnd-cert"),
        document.getElementById("twr-cert"),
        document.getElementById("dep-cert"),
        document.getElementById("app-cert"),
        document.getElementById("ctr-cert")
    ];
    for (let i = 0; i < certs.length; i++) {
        let cert = certs[i];
        let obj = htmls[i];
        switch(cert.toString()) {
            case "0":
                obj.style.backgroundColor = "white";
                obj.innerText = "Not Certed";
                obj.style.color = "black";
                break;
            case "1":
                obj.style.backgroundColor = "blue";
                obj.innerText = "Training";
                obj.style.color = "black";
                break;
            case "2":
                obj.style.backgroundColor = "orange";
                obj.innerText = "Solo Cert";
                obj.style.color = "black";
                break;
            case "3":
                obj.style.backgroundColor = "green";
                obj.innerText = "Certed";
                obj.style.color = "black";
                break;
        }
    }
}