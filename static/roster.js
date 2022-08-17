function create_UUID(){
    let dt = new Date().getTime();
    let uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = (dt + Math.random()*16)%16 | 0;
        dt = Math.floor(dt/16);
        return (c=='x' ? r :(r&0x3|0x8)).toString(16);
    });
    return uuid;
}

function certs2List(certs) {
    let rawcert = certs.toString().split("");
    if (rawcert.length == 1) {
        rawcert = [0, 0, 0, 0, 0, 0];
    }
    let cconstruct = [];
    for (let cert of rawcert) {
        let color = "";
        let text = "";
        switch(cert.toString()) {
            case "0":
                color = "white";
                text = "Not Certified";
                break;
            case "1":
                color = "blue";
                text = "In Training";
                break;
            case "2":
                color = "orange";
                text = "Solo Certified";
                break;
            case "3":
                color = "green";
                text = "Certified";
                break;
        }
        cconstruct.push([color, text]);
    }
    console.log(cconstruct);
    return cconstruct;
}

async function displayRosterData(roster) {
    let counter = 0;
    const rostertab = document.getElementById("cert-table");
	for (let member of roster) {
	    let rating = member[2];
	    let qualifiedname = "";
        switch(rating.toString()) {
            case "1":
                qualifiedname = "Observer";
                break;
            case "2":
                qualifiedname = "Student 1";
                break;
            case "3":
                qualifiedname = "Student 2";
                break;
            case "4":
                qualifiedname = "Student 3";
                break;
            case "5":
                qualifiedname = "Controller 1";
                break;
            case "7":
                qualifiedname = "Controller 3";
                break;
            case "8":
                qualifiedname = "Instructor 1";
                break;
            case "10":
                qualifiedname = "Instructor 3";
                break;
            case "11":
                qualifiedname = "Supervisor";
                break;
            case "12":
                qualifiedname = "Administrator";
                break;
        }
		let element = document.createElement("tr");
        let certs = certs2List(member[4]);
		element.id = `row-${counter}`;
        element.innerHTML = `
            <td>${member[0]}</td>
            <td>${member[1]}</td>
            <td class="cell"><p id="rating">${qualifiedname}</p></td>
            <td class="cell"><p id="visitor">${member[3]}</p></td>
            <td class="cell"><p id="del-cert-${counter}" style="background-color:${certs[0][0]}">${certs[0][1]}</p></td>
            <td class="cell"><p id="gnd-cert-${counter}" style="background-color:${certs[1][0]}">${certs[1][1]}</p></td>
            <td class="cell"><p id="twr-cert-${counter}" style="background-color:${certs[2][0]}">${certs[2][1]}</p></td>
            <td class="cell"><p id="dep-cert-${counter}" style="background-color:${certs[3][0]}">${certs[3][1]}</p></td>
            <td class="cell"><p id="app-cert-${counter}" style="background-color:${certs[4][0]}">${certs[4][1]}</p></td>
            <td class="cell"><p id="ctr-cert-${counter}" style="background-color:${certs[5][0]}">${certs[5][1]}</p></td>
        `
        rostertab.appendChild(element);
	}
}

async function getRosterData() {
    const sock = io();
    let uid = create_UUID();
    sock.on("connect", (data) => {
        console.log("Connected to WSS");
    });
    sock.on("upgrade", (data) => {
        console.log(data)
    });
    sock.on("ROSTER REQUEST", async (data) => {
        if (data["uuid"] != uid) {

        }
        else {
            let roster = data['roster'];
            await displayRosterData(roster);
        }
    });
    sock.emit("REQUEST ROSTER", {
        "uuid": uid
    });
    while (!sock.connected) {

    }
	return sock;
}