function toastFactory(type, title, text, time, showConfirmButton) {
    const Toast = Swal.mixin({
        toast: true,
        position: 'top-start',
        showConfirmButton: showConfirmButton || false,
        timer: time || '3000',
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.addEventListener('mouseenter', Swal.stopTimer);
            toast.addEventListener('mouseleave', Swal.resumeTimer);
        },
    });

    Toast.fire({
        icon: type,
        title: '<strong>' + title + '</strong>',
        html: text,
    });
}

steamids = {};
driverdata = {};
ets2data = {};
atsdata = {};
membersteam = {};
memberuserid = {};

function UpdateSteam() {
    $.ajax({
        url: "https://drivershub.charlws.com/atm/member/steam",
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            l = data.response.list;
            for (var i = 0; i < l.length; i++) {
                membersteam[l[i].steamid] = l[i].name;
                memberuserid[l[i].steamid] = l[i].userid;
            }
        }
    });
}
UpdateSteam();
setInterval(UpdateSteam, 60000);

const etssocket = new WebSocket('wss://gateway.navio.app/');
etssocket.addEventListener("open", () => {
    etssocket.send(
        JSON.stringify({
            op: 1,
            data: {
                "subscribe_to_company": 25,
                //"subscribe_to_all_drivers": true,
                "game": "eut2"
            },
        }),
    );
});

etssocket.addEventListener("message", ({
    data: message
}) => {
    let {
        type,
        data
    } = JSON.parse(message)

    if (type === "AUTH_ACK") {
        setInterval(() => {
            etssocket.send(
                JSON.stringify({
                    op: 2,
                }),
            );
        }, data.heartbeat_interval * 1000);
    }

    if (type === "TELEMETRY_UPDATE") {
        steamids[data.driver] = +new Date();
        driverdata[data.driver] = data;
        ets2data[data.driver] = data;
    }

    if (type === "NEW_EVENT") {
        if (data.type == 1) {
            drivername = membersteam[data.driver];
            if (drivername == "undefined" || drivername == undefined) drivername = "Unknown Driver";
            toastFactory("success", "Job Delivery", "<b>" + drivername + "</b><br><b>Distance:</b> " + TSeparator(parseInt(data.distance / 1.6)) + "Mi<br><b>Revenue:</b> €" + TSeparator(data.revenue), 30000, false);
        }
    }
});

const atssocket = new WebSocket('wss://gateway.navio.app/');
atssocket.addEventListener("open", () => {
    atssocket.send(
        JSON.stringify({
            op: 1,
            data: {
                "subscribe_to_company": 25,
                //"subscribe_to_all_drivers": true,
                "game": "ats"
            },
        }),
    );
});

atssocket.addEventListener("message", ({
    data: message
}) => {
    let {
        type,
        data
    } = JSON.parse(message)

    if (type === "AUTH_ACK") {
        setInterval(() => {
            atssocket.send(
                JSON.stringify({
                    op: 2,
                }),
            );
        }, data.heartbeat_interval * 1000);
    }

    if (type === "TELEMETRY_UPDATE") {
        steamids[data.driver] = +new Date();
        driverdata[data.driver] = data;
        atsdata[data.driver] = data;
    }

    if (type === "NEW_EVENT") {
        if (data.type == 1) {
            drivername = membersteam[data.driver];
            if (drivername == "undefined" || drivername == undefined) drivername = "Unknown Driver";
            toastFactory("success", "Job Delivery", "<b>" + drivername + "</b><br><b>Distance:</b> " + TSeparator(parseInt(data.distance / 1.6)) + "Mi<br><b>Revenue:</b> $" + TSeparator(data.revenue), 30000, false);
        }
    }
});

function CountOnlineDriver() {
    drivers = Object.keys(steamids);
    for (var i = 0; i < drivers.length; i++) {
        if (+new Date() - steamids[drivers[i]] > 120000) {
            delete steamids[drivers[i]];
            delete driverdata[drivers[i]];
        }
    }
    return Object.keys(steamids).length;
}

setInterval(function () {
    cnt = CountOnlineDriver()
    $("#livedriver").html(cnt);
    dt = new Date();
    t = pad(dt.getHours(), 2) + ":" + pad(dt.getMinutes(), 2) + ":" + pad(dt.getSeconds(), 2);
    $("#livedriverdt").html(t);

    $("#onlinedriver").empty();
    if (cnt == 0) {
        $("#onlinedriverHead").hide();
        $("#onlinedriver").append(`
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
        return;
    }
    $("#onlinedriverHead").show();

    for (var i = 0; i < cnt; i++) {
        steamid = Object.keys(steamids)[i];
        drivername = membersteam[steamid];
        if (drivername == "undefined" || drivername == undefined) drivername = "Unknown";
        d = driverdata[steamid];
        truck = d.truck.brand.name + " " + d.truck.name;
        cargo = "<i>Free roaming</i>";
        if (d.job != null)
            cargo = d.job.cargo.name;
        speed = parseInt(d.truck.speed * 3.6 / 1.6) + "Mi/h";
        distance = TSeparator(parseInt(d.truck.navigation.distance / 1000 / 1.6)) + "." + String(parseInt(d.truck.navigation.distance / 1.6) % 1000).substring(0, 1) + "Mi";
        $("#onlinedriver").append(`
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">${drivername}</td>
              <td class="py-5 px-6 font-medium">${truck}</td>
              <td class="py-5 px-6 font-medium">${cargo}</td>
              <td class="py-5 px-6 font-medium">${speed}</td>
              <td class="py-5 px-6 font-medium">${distance}</td>
            </tr>`);
    }
}, 1000);

function PlayerPoint(steamid){
    drivername = membersteam[steamid];
    userid = memberuserid[steamid];
    if (drivername == "undefined" || drivername == undefined) drivername = "Unknown";
    d = driverdata[steamid];
    truck = d.truck.brand.name + " " + d.truck.name;
    cargo = "<i>Free roaming</i>";
    if (d.job != null)
        cargo = d.job.cargo.name;
    speed = parseInt(d.truck.speed * 3.6 / 1.6) + "Mi/h";
    distance = TSeparator(parseInt(d.truck.navigation.distance / 1000 / 1.6)) + "." + String(parseInt(d.truck.navigation.distance / 1.6) % 1000).substring(0, 1) + "Mi";
    toastFactory("info", drivername, `<b>Truck: </b>${truck}<br><b>Cargo: </b>${cargo}<br><b>Speed: </b>${speed}<br><a style='cursor:pointer' onclick='loadProfile(${userid})'>Show profile</a>`, 5000, false);
}

function RenderPoint(mapid, steamid, x, y, scale) {
    console.log("Render point " + x + ", " + y);
    maph = $("#" + mapid).height();
    x = parseInt(-maph + x);
    y = parseInt(y);
    drivername = membersteam[steamid];
    if(scale <= 10){
        $("#" + mapid).append(`<a style='cursor:pointer;color:skyblue;' onclick="PlayerPoint('${steamid}')";><span class="${mapid}-player""; style='curosr:pointer;position:relative;top:${x-30}px;left:${y-23.5}px;text-align:center'>${drivername}</span></a>`);
        $("#" + mapid).append(`<a style='cursor:pointer' onclick="PlayerPoint('${steamid}')";><span class="dot ${mapid}-player""; style='curosr:pointer;position:relative;top:${x-7.5}px;left:${y-47.5}px'></span></a>`);
    } else if(scale <= 25){
        $("#" + mapid).append(`<span class="dot-small ${mapid}-player""; style='curosr:pointer;position:relative;top:${x-47.5}px;left:${y}px'></span>`);
        $("#" + mapid).append(`<a style='cursor:pointer' onclick="PlayerPoint('${steamid}')";><span class="dot-area ${mapid}-player""; style='curosr:pointer;position:relative;top:${x-27.5}px;left:${y-30}px'></span></a>`);
    } else {
        $("#" + mapid).append(`<a style='cursor:pointer' onclick="PlayerPoint('${steamid}')";><span class="dot-area ${mapid}-player""; style='curosr:pointer;position:relative;top:${x-27.5}px;left:${y-27.5}px'></span></a>`);      
    }
}

window.n = {};
setInterval(function () {
    if (!ets2loaded || window.n == undefined || window.n.previousExtent_ == undefined) return;
    window.mapRange = {};
    mapRange["top"] = window.n.previousExtent_[3];
    mapRange["left"] = window.n.previousExtent_[0];
    mapRange["bottom"] = window.n.previousExtent_[1];
    mapRange["right"] = window.n.previousExtent_[2];
    $(".map-player").remove();
    players = Object.keys(ets2data);
    for (var i = 0; i < players.length; i++) {
        pos = ets2data[players[i]].truck.position;
        x = pos.x;
        z = -pos.z;
        mapxl = mapRange["left"];
        mapxr = mapRange["right"];
        mapyt = mapRange["top"];
        mapyb = mapRange["bottom"];
        mapw = $("#map").width();
        maph = $("#map").height();
        scale = (mapxr - mapxl) / $("#map").width();
        if (x > mapxl && x < mapxr && z > mapyb && z < mapyt) {
            rx = (x - mapxl) / (mapxr - mapxl) * mapw;
            rz = (z - mapyt) / (mapyb - mapyt) * maph;
            RenderPoint("map", players[i], rz, rx, scale);
        }
    }
}, 500);

window.an = {};
setInterval(function () {
    if (!atsloaded || window.an == undefined || window.an.previousExtent_ == undefined) return;
    window.amapRange = {};
    amapRange["top"] = window.an.previousExtent_[3];
    amapRange["left"] = window.an.previousExtent_[0];
    amapRange["bottom"] = window.an.previousExtent_[1];
    amapRange["right"] = window.an.previousExtent_[2];
    $(".amap-player").remove();
    aplayers = Object.keys(atsdata);
    for (var i = 0; i < aplayers.length; i++) {
        apos = atsdata[aplayers[i]].truck.position;
        ax = apos.x;
        az = -apos.z;
        amapxl = amapRange["left"];
        amapxr = amapRange["right"];
        amapyt = amapRange["top"];
        amapyb = amapRange["bottom"];
        amapw = $("#amap").width();
        amaph = $("#amap").height();
        ascale = (amapxr - amapxl) / $("#amap").width();
        if (ax > amapxl && ax < amapxr && az > amapyb && az < amapyt) {
            arx = (ax - amapxl) / (amapxr - amapxl) * amapw;
            arz = (az - amapyt) / (amapyb - amapyt) * amaph;
            RenderPoint("amap", aplayers[i], arz, arx, ascale);
        }
    }
}, 500);