steamids = {};
driverdata = {};
const socket = new WebSocket('wss://gateway.navio.app/');
socket.addEventListener("open", () => {
    socket.send(
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

    if (type === "NEW_EVENT" || type === "TELEMETRY_UPDATE") {
        steamids[data.driver] = +new Date();
        driverdata[data.driver] = data;
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

membersteam = {};
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
        }
    }
});

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
        name = membersteam[parseInt(steamid)];
        if (name == "undefined" || name == undefined) name = "Unknown";
        d = driverdata[steamid];
        truck = d.truck.brand.name + " " + d.truck.name;
        cargo = "<i>Free roaming</i>";
        if (d.job != null)
            cargo = d.job.cargo.name;
        speed = parseInt(d.truck.speed / 1.6) + "Mi/h";
        distance = TSeparator(parseInt(d.truck.navigation.distance / 1.6)) + "Mi";
        $("#onlinedriver").append(`
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">${name}</td>
              <td class="py-5 px-6 font-medium">${truck}</td>
              <td class="py-5 px-6 font-medium">${cargo}</td>
              <td class="py-5 px-6 font-medium">${speed}</td>
              <td class="py-5 px-6 font-medium">${distance}</td>
            </tr>`);
    }
}, 1000);