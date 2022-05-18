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

const socket = new WebSocket('wss://gateway.navio.app/');
socket.addEventListener("open", () => {
    socket.send(
        JSON.stringify({
            op: 1,
            data: {
                "subscribe_to_company": 25,
                //"subscribe_to_all_drivers": true
            },
        }),
    );
});

socket.addEventListener("message", ({
    data: message
}) => {
    let {
        type,
        data
    } = JSON.parse(message)

    if (type === "AUTH_ACK") {
        setInterval(() => {
            socket.send(
                JSON.stringify({
                    op: 2,
                }),
            );
        }, data.heartbeat_interval * 1000);
    }

    if (type === "TELEMETRY_UPDATE") {
        steamids[data.driver] = +new Date();
        driverdata[data.driver] = data;
        if(data.game.id == "eut2") ets2data[data.driver] = data;
        else if(data.game.id == "ats") atsdata[data.driver] = data;
    }

    if (type === "NEW_EVENT") {
        if (data.type == 1) {
            drivername = membersteam[data.driver];
            if (drivername == "undefined" || drivername == undefined) drivername = "Unknown Driver";
            toastFactory("success", "Job Delivery", "<b>" + drivername + "</b><br><b>Distance:</b> " + TSeparator(parseInt(data.distance / 1.6)) + "Mi<br><b>Revenue:</b> €" + TSeparator(data.revenue), 30000, false);
        }
    }
});

function CountOnlineDriver() {
    drivers = Object.keys(steamids);
    for (var i = 0; i < drivers.length; i++) {
        if (+new Date() - steamids[drivers[i]] > 120000) {
            if(driverdata[drivers[i]].game.id == "eut2") delete ets2data[drivers[i]];
            else if(driverdata[drivers[i]].game.id == "ats") delete atsdata[drivers[i]];
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
            <tr class="text-xs">
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
        userid = memberuserid[steamid];
        if (drivername == "undefined" || drivername == undefined) drivername = "Unknown";
        d = driverdata[steamid];
        truck = d.truck.brand.name + " " + d.truck.name;
        cargo = "<i>Free roaming</i>";
        if (d.job != null)
            cargo = d.job.cargo.name;
        speed = parseInt(d.truck.speed * 3.6 / 1.6) + "Mi/h";
        distance = TSeparator(parseInt(d.truck.navigation.distance / 1000 / 1.6)) + "." + String(parseInt(d.truck.navigation.distance / 1.6) % 1000).substring(0, 1) + "Mi";
        $("#onlinedriver").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium"><a style='cursor:pointer' onclick='loadProfile(${userid})'>${drivername}</a></td>
              <td class="py-5 px-6 font-medium">${truck}</td>
              <td class="py-5 px-6 font-medium">${cargo}</td>
              <td class="py-5 px-6 font-medium">${speed}</td>
              <td class="py-5 px-6 font-medium">${distance}</td>
            </tr>`);
    }
}, 1000);

function PlayerPoint(steamid){
    if(steamid == 0 || steamid == "0") return;
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

trucksvg = `<svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-truck-delivery" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" color="red" fill="none" stroke-linecap="round" stroke-linejoin="round"> <path stroke="none" d="M0 0h24v24H0z" fill="none"/> <circle cx="7" cy="17" r="2" /> <circle cx="17" cy="17" r="2" /> <path d="M5 17h-2v-4m-1 -8h11v12m-4 0h6m4 0h2v-6h-8m0 -5h5l3 5" /> <line x1="3" y1="9" x2="7" y2="9" /> </svg> `;

function RenderPoint(mapid, steamid, x, y, scale, nodetail = false, truckicon = false) {
    // console.log("Render point " + x + ", " + y);
    maph = $("#" + mapid).height();
    //x = -maph + x;
    drivername = membersteam[steamid];
    t = $("#" + mapid).position().top;
    l = $("#" + mapid).position().left;
    if(truckicon){
        $("#" + mapid).append(`<a class="${mapid}-player" style='cursor:pointer;position:absolute;top:${t+x-12}px;left:${l+y-12}px' onclick="PlayerPoint('${steamid}')";>${trucksvg}</a>`);
        return;
    }
    if(scale <= 10){
        if(!nodetail)  $("#" + mapid).append(`<a class="${mapid}-player" style='cursor:pointer;position:absolute;top:${t+x-30}px;left:${l+y-7.5}px;text-align:center;color:skyblue' onclick="PlayerPoint('${steamid}')";>${drivername}</a>`);
        $("#" + mapid).append(`<a class="${mapid}-player dot" style='cursor:pointer;position:absolute;top:${t+x-7.5}px;left:${l+y-7.5}px' onclick="PlayerPoint('${steamid}')";></a>`);
    } else if(scale <= 25){
        $("#" + mapid).append(`<a class="${mapid}-player dot-small" style='cursor:pointer;position:absolute;top:${t+x-5}px;left:${l+y-5}px' onclick="PlayerPoint('${steamid}')"></a>`);
        $("#" + mapid).append(`<a class="${mapid}-player dot-area" style='cursor:pointer;position:absolute;top:${t+x-25}px;left:${l+y-25}px' onclick="PlayerPoint('${steamid}')"></a>`);
    } else {
        $("#" + mapid).append(`<a class="${mapid}-player dot-area" style='cursor:pointer;position:absolute;top:${t+x-25}px;left:${l+y-25}px' onclick="PlayerPoint('${steamid}')"></a>`);      
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
        if (Object.keys(ets2data).indexOf(players[i]) == -1) {
            delete ets2data[players[i]];
            continue;
        }
        if (JSON.stringify(ets2data[players[i]]).toLowerCase().indexOf("promod") != -1) continue; // bypass promod on base map
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
        if (Object.keys(atsdata).indexOf(players[i]) == -1) {
            delete atsdata[players[i]];
            continue;
        }
        if (JSON.stringify(atsdata[players[i]]).toLowerCase().indexOf("promod") != -1) continue; // bypass promod on base map
        if (JSON.stringify(atsdata[players[i]]).toLowerCase().indexOf("coast to coast") != -1) continue; // bypass coast to coast on base map
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