rolelist = {};
dmapint = -1;
window.mapcenter = {}
window.autofocus = {}

isdark = parseInt(localStorage.getItem("darkmode"));
if (localStorage.getItem("darkmode") == undefined) isdark = 1;
rolelist = localStorage.getItem("rolelist");
if (rolelist != undefined && rolelist != null) {
    rolelist = JSON.parse(rolelist);
} else {
    rolelist = [];
}

positions = localStorage.getItem("positions");
if (positions != undefined && positions != null) {
    positions = JSON.parse(positions);
    positionstxt = "";
    for (var i = 0; i < positions.length; i++) {
        positionstxt += positions[i] + "\n";
        $("#sa-select").append("<option>" + positions[i] + "</option>");
    }
    positionstxt = positionstxt.slice(0, -1);
    $("#staffposedit").val(positionstxt);
} else {
    positions = [];
}

function DarkMode() {
    if (!isdark) {
        $("body").css("transition", "color 1000ms linear");
        $("body").css("transition", "background-color 1000ms linear");
        $("body").addClass("bg-gray-800");
        $("body").css("color", "white");
        $("head").append(`<style id='convertbg'>
            h1,h2,h3,p,span,text,label,input,textarea,select,tr {color: white;transition: color 1000ms linear;}
            svg{transition: color 1000ms linear;}
            .text-gray-500,.text-gray-600 {color: #ddd;transition: color 1000ms linear;}
            .bg-white {background-color: rgba(255, 255, 255, 0.2);transition: background-color 1000ms linear;}
            .swal2-popup {background-color: rgb(41 48 57)}
            .rounded-full {background-color: #888;transition: background-color 1000ms linear;}</style>`);
        $("#todarksvg").hide();
        $("#tolightsvg").show();
        Chart.defaults.color = "white";
        $("body").html($("body").html().replaceAll("text-green", "text-temp"));
        $("body").html($("body").html().replaceAll("#382CDD", "skyblue").replaceAll("green", "lightgreen"));
        $("body").html($("body").html().replaceAll("text-temp", "text-green"));
    } else {
        $("body").css("transition", "color 1000ms linear");
        $("body").css("transition", "background-color 1000ms linear");
        $("body").removeClass("bg-gray-800");
        $("body").css("color", "");
        $("head").append(`<style id='convertbg2'>
            h1,h2,h3,p,span,text,label,input,textarea,select,tr {transition: color 1000ms linear;}
            svg{transition: color 1000ms linear;}
            .text-gray-500,.text-gray-600 {transition: color 1000ms linear;}
            .bg-white {background-color: white;transition: background-color 1000ms linear;}
            .swal2-popup {background-color: white;}
            .rounded-full {background-color: #ddd;transition: background-color 1000ms linear;}</style>`);
        setTimeout(function () {
            $("#convertbg2").remove();
        }, 1000);
        $("#convertbg").remove();
        $("#todarksvg").show();
        $("#tolightsvg").hide();
        Chart.defaults.color = "black";
        $("body").html($("body").html().replaceAll("#382CDD", "skyblue").replaceAll("lightgreen", "green"));
    }
    isdark = 1 - isdark;
    localStorage.setItem("darkmode", isdark);
    loadStats();
}

token = localStorage.getItem("token");
$(".pageinput").val("1");
sc = undefined;
chartscale = 2;
addup = 0;

async function loadChart(userid = -1) {
    if (userid != -1) {
        $(".ucs").css("background-color", "");
        $("#ucs" + chartscale).css("background-color", "lightblue");
        $("#uaddup" + addup).css("background-color", "lightblue");
    } else {
        $(".cs").css("background-color", "");
        $("#cs" + chartscale).css("background-color", "lightblue");
        $("#addup" + addup).css("background-color", "lightblue");
    }
    pref = "s";
    if (userid != -1) pref = "userS";
    $.ajax({
        url: "https://drivershub.charlws.com/atm/dlog/chart?scale=" + chartscale + "&addup=" + addup + "&quserid=" + userid,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            d = data.response;
            const ctx = document.getElementById(pref + 'tatisticsChart').getContext('2d');
            labels = [];
            distance = [];
            fuel = [];
            euro = [];
            dollar = [];
            for (i = 0; i < d.length; i++) {
                ts = d[i].starttime;
                ts = new Date(ts * 1000);
                if (chartscale == 1) { // 24h
                    ts = pad(ts.getHours(), 2) + ":" + pad(ts.getMinutes(), 2);
                } else if (chartscale >= 2) { // 7 d / 30 d
                    ts = pad(ts.getDate(), 2) + "/" + pad((ts.getMonth() + 1), 2);
                }
                labels.push(ts);
                if (d[i].distance == 0) {
                    distance.push(NaN);
                    fuel.push(NaN);
                    euro.push(NaN);
                    dollar.push(NaN);
                    continue;
                }
                distance.push(parseInt(d[i].distance / 1.6));
                fuel.push(d[i].fuel);
                euro.push(parseInt(d[i].euro));
                dollar.push(parseInt(d[i].dollar));
            }
            const skipped = (ctx, value) => ctx.p0.skip || ctx.p1.skip ? value : undefined;
            const config = {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Distance (Mi)',
                        data: distance,
                        borderColor: "lightgreen",
                        cubicInterpolationMode: 'monotone',
                        segment: {
                            borderColor: ctx => skipped(ctx, 'rgb(0,0,0,0.2)'),
                            borderDash: ctx => skipped(ctx, [6, 6]),
                        },
                        spanGaps: true,
                        xAxisID: 'x',
                        yAxisID: 'y',
                        type: 'line'
                    }, {
                        label: 'Fuel (L)',
                        data: fuel,
                        borderColor: "orange",
                        cubicInterpolationMode: 'monotone',
                        segment: {
                            borderColor: ctx => skipped(ctx, 'rgb(0,0,0,0.2)'),
                            borderDash: ctx => skipped(ctx, [6, 6]),
                        },
                        spanGaps: true,
                        xAxisID: 'x',
                        yAxisID: 'y',
                        type: 'line'
                    }, {
                        label: 'Profit (€)',
                        data: euro,
                        backgroundColor: "lightblue",
                        xAxisID: 'x1',
                        yAxisID: 'y1'
                    }, {
                        label: 'Profit ($)',
                        data: dollar,
                        backgroundColor: "pink",
                        xAxisID: 'x1',
                        yAxisID: 'y1'
                    }, ]
                },
                showTooltips: true,
                options: {
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false
                    },
                    radius: 0,
                    scales: {
                        x: {
                            display: false
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                        },
                        x1: {
                            stacked: true,
                        },
                        y1: {
                            display: true,
                            position: 'right',
                            stacked: true,

                            grid: {
                                drawOnChartArea: false,
                            },
                        },
                    }
                }
            };
            if (sc != undefined) {
                sc.destroy();
                $(pref + 'tatisticsChart').remove();
            }
            sc = new Chart(ctx, config);
        }
    });
}

deliveryStatsChart = undefined;

function loadStats(basic = false) {
    if (curtab != "#HomeTab" && curtab != "#Delivery") return;
    loadChart();
    $.ajax({
        url: "https://drivershub.charlws.com/atm/dlog/stats",
        type: "GET",
        dataType: "json",
        success: function (data) {
            d = data.response;
            drivers = sigfig(parseInt(d.drivers));
            newdrivers = sigfig(parseInt(d.newdrivers));
            drivers = drivers.split(".")[0];
            newdrivers = newdrivers.split(".")[0];
            jobs = sigfig(parseInt(d.jobs));
            newjobs = sigfig(parseInt(d.newjobs));
            jobs = jobs.split(".")[0];
            newjobs = newjobs.split(".")[0];
            distance = sigfig(d.distance / 1.6) + "Mi";
            newdistance = sigfig(d.newdistance / 1.6) + "Mi";
            europrofit = "€" + sigfig(d.europrofit);
            neweuroprofit = "€" + sigfig(d.neweuroprofit);
            dollarprofit = "$" + sigfig(d.dollarprofit);
            newdollarprofit = "$" + sigfig(d.newdollarprofit);
            fuel = sigfig(d.fuel) + "L";
            newfuel = sigfig(d.newfuel) + "L";
            $("#alldriver").html(drivers);
            $("#newdriver").html(newdrivers);
            $("#alldistance").html(distance);
            $("#newdistance").html(newdistance);
            $("#alljob").html(jobs);
            $("#newjob").html(newjobs);
            $("#allprofit").html(europrofit + " + " + dollarprofit);
            $("#newprofit").html(neweuroprofit + " + " + newdollarprofit);
            $("#dprofit").html(neweuroprofit + " + " + newdollarprofit);
            $("#allfuel").html(fuel);
            $("#newfuel").html(newfuel);

            driver_of_the_day = d.driver_of_the_day;
            discordid = driver_of_the_day.discordid;
            avatar = driver_of_the_day.avatar;
            if (avatar != null) {
                if (avatar.startsWith("a_"))
                    src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif";
                else
                    src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png";
            } else {
                avatar = "/images/atm-black.png";
            }
            distance = TSeparator(parseInt(driver_of_the_day.distance / 1.6));
            $("#dotd").html(`<img src="${src}" style="width:20px;border-radius:100%;display:inline"> <b>${driver_of_the_day.name}</b>`);
            $("#dotddistance").html(`Driven ${distance} Miles`);

            $("#dalljob").html(newjobs);
            $("#dtotdistance").html(newdistance.replaceAll("Mi", " Miles"));

            const ctx = document.getElementById('deliveryStatsChart').getContext('2d');
            const config = {
                type: 'pie',
                data: {
                    labels: ['Euro Truck Simulator 2', 'American Truck Simulator'],
                    datasets: [{
                        label: 'Game Preference',
                        data: [d.ets2jobs, d.atsjobs],
                        backgroundColor: ["lightblue", "pink"],
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: 'Game Preference'
                        }
                    }
                },
            };
            if (deliveryStatsChart != undefined) deliveryStatsChart.destroy();
            deliveryStatsChart = new Chart(ctx, config);
        }
    });
    if (token.length != 36 || !isNumber(localStorage.getItem("userid")) || localStorage.getItem("userid") == -1) return; // guest / invalid
    if (!basic) {
        $.ajax({
            url: "https://drivershub.charlws.com/atm/dlog/leaderboard",
            type: "GET",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + token
            },
            success: function (data) {
                if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
                users = data.response.list;
                $("#leaderboard").empty();
                for (var i = 0; i < Math.min(users.length, 5); i++) {
                    user = users[i];
                    userid = user.userid;
                    name = user.name;
                    discordid = user.discordid;
                    avatar = user.avatar;
                    totalpnt = TSeparator(parseInt(user.totalpnt));
                    if (avatar != null) {
                        if (avatar.startsWith("a_"))
                            src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif";
                        else
                            src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png";
                    } else {
                        avatar = "/images/atm-black.png";
                    }
                    $("#leaderboard").append(`<tr class="text-xs">
              <td class="py-5 px-6 font-medium">
                <a style="cursor: pointer" onclick="loadProfile(${userid})"><img src='${src}' width="20px" style="display:inline;border-radius:100%"> ${name}</a></td>
              <td class="py-5 px-6">${totalpnt}</td>
            </tr>`);
                }
            }
        });
        $.ajax({
            url: "https://drivershub.charlws.com/atm/dlog/newdrivers",
            type: "GET",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + token
            },
            success: function (data) {
                if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
                users = data.response.list;
                $("#newdriverTable").empty();
                for (var i = 0; i < Math.min(users.length, 5); i++) {
                    user = users[i];
                    userid = user.userid;
                    name = user.name;
                    discordid = user.discordid;
                    avatar = user.avatar;
                    dt = new Date(user.joints * 1000);
                    joindt = pad(dt.getDate(), 2) + "/" + pad(dt.getMonth() + 1, 2);
                    if (avatar != null) {
                        if (avatar.startsWith("a_"))
                            src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif";
                        else
                            src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png";
                    } else {
                        avatar = "/images/atm-black.png";
                    }
                    $("#newdriverTable").append(`<tr class="text-xs">
              <td class="py-5 px-6 font-medium">
                <a style="cursor: pointer" onclick="loadProfile(${userid})"><img src='${src}' width="20px" style="display:inline;border-radius:100%"> ${name}</a></td>
              <td class="py-5 px-6">${joindt}</td>
            </tr>`);
                }
            }
        });
    }
}

eventsCalendar = undefined;
curtab = "#HomeTab";

loadworking = false;
async function GeneralLoad() {
    if (loadworking) return;
    loadworking = true;
    if (isdark) $("#loading").css("border", "solid lightgreen 1px");
    else $("#loading").css("border", "solid green 1px");
    $("#loading").css("width", "50%");
    maxajax = 0;
    lastw = 0;
    while ($.active > 0) {
        maxajax = Math.max($.active + 1, maxajax);
        neww = parseInt(100 - $.active / maxajax * 100);
        while (neww > lastw) {
            lastw += 1;
            $("#loading").css("width", `${lastw}%`);
            await sleep(5);
        }
        await sleep(10);
    }
    neww = 100;
    while (neww > lastw) {
        lastw += 1;
        $("#loading").css("width", `${lastw}%`);
        await sleep(5);
    }
    neww = 1;
    while (neww < lastw) {
        lastw -= 5;
        $("#loading").css("width", `${lastw}%`);
        await sleep(1);
    }
    $("#loading").css("border", "solid transparent 1px");
    loadworking = false;
}

async function ShowTab(tabname, btnname) {
    loadworking = true;
    $("html, body").animate({
        scrollTop: 0
    }, "slow");
    curtab = tabname;
    clearInterval(dmapint);
    dmapint = -1;
    $("#map,#dmap,#pmap,#amap").children().remove();
    setTimeout(async function () {
        if (isdark) $("#loading").css("border", "solid lightgreen 1px");
        else $("#loading").css("border", "solid green 1px");
        $("#loading").css("width", "50%");
        maxajax = 0;
        lastw = 0;
        while ($.active > 0) {
            maxajax = Math.max($.active + 1, maxajax);
            neww = parseInt(100 - $.active / maxajax * 100);
            while (neww > lastw) {
                lastw += 1;
                $("#loading").css("width", `${lastw}%`);
                await sleep(5);
            }
            await sleep(10);
        }
        neww = 100;
        while (neww > lastw) {
            lastw += 1;
            $("#loading").css("width", `${lastw}%`);
            await sleep(5);
        }
        $(".tabs").hide();
        $(tabname).show();
        neww = 1;
        while (neww < lastw) {
            lastw -= 5;
            $("#loading").css("width", `${lastw}%`);
            await sleep(1);
        }
        if (tabname != "#Event") {
            eventsCalendar = undefined;
            $("#eventsCalendar").children().remove();
            $("#eventsCalendar").attr("class", "");
        }
        $("#loading").css("border", "solid transparent 1px");
        loadworking = false;
    }, 10);
    $(".tabbtns").removeClass("bg-indigo-500");
    $(btnname).addClass("bg-indigo-500");
    if (tabname == "#Map") {
        window.history.pushState("", "", '/map');
        window.autofocus["map"] = -2;
        window.autofocus["amap"] = -2;
        window.autofocus["pmap"] = -2;
        setTimeout(async function () {
            while ($("#loading").width() != 0) await sleep(50);
            LoadETS2Map();
            LoadETS2PMap();
            LoadATSMap();
        }, 50);
    }
    if (tabname == "#HomeTab") {
        window.history.pushState("", "", '/');
        loadStats();
    }
    if (tabname == "#AnnTab") {
        window.history.pushState("", "", '/announcement');
        ch = $("#anns").children();
        ch.hide();
        for (var i = 0; i < ch.length; i++) {
            $(ch[i]).fadeIn();
            await sleep(200);
        }
    }
    if (tabname == "#StaffAnnTab") {
        window.history.pushState("", "", '/staffannouncement');
    }
    if (tabname == "#Ranking") {
        window.history.pushState("", "", '/ranking');
    }
    if (tabname == "#SubmitApp") {
        window.history.pushState("", "", '/submitapp');
        $("#driverappsel").attr("selected", "selected");
    }
    if (tabname == "#MyApp") {
        window.history.pushState("", "", '/myapp');
        loadMyApp();
    }
    if (tabname == "#AllApp") {
        window.history.pushState("", "", '/allapp');
        loadAllApp();
    }
    if (tabname == "#AllUsers") {
        window.history.pushState("", "", '/pendinguser');
        loadUsers();
    }
    if (tabname == "#AllMembers") {
        window.history.pushState("", "", '/member');
        loadMembers();
    }
    if (tabname == "#StaffMembers") {
        window.history.pushState("", "", '/staffmember');
        loadMembers();
    }
    if (tabname == "#Delivery") {
        window.history.pushState("", "", '/delivery');
        loadStats(true);
        loadDelivery();
    }
    if (tabname == "#Event") {
        window.history.pushState("", "", '/event');
        loadEvent();
    }
    if (tabname == "#StaffEvent") {
        window.history.pushState("", "", '/staffevent');
        loadEvent();
    }
    if (tabname == "#ProfileTab") {
        if (isNumber(btnname)) userid = btnname;
        else userid = localStorage.getItem("userid");
        window.history.pushState("", "", '/member?userid=' + userid);
        loadProfile(userid);
    }
    if (tabname == "#AuditLog") {
        window.history.pushState("", "", '/audit');
        loadAuditLog();
    }
    if (tabname == "#Leaderboard") {
        window.history.pushState("", "", '/leaderboard');
        loadLeaderboard();
    }
}

function FetchAnnouncement() {
    aid = $("#annid").val();

    GeneralLoad();
    $("#fetchAnnouncementBtn").html("Working...");
    $("#fetchAnnouncementBtn").attr("disabled", "disabled");

    $.ajax({
        url: "https://drivershub.charlws.com/atm/announcement?aid=" + aid,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#fetchAnnouncementBtn").html("Fetch Data");
            $("#fetchAnnouncementBtn").removeAttr("disabled");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);

            const announcement = data.response;
            $("#anntitle").val(announcement.title);
            $("#anncontent").val(announcement.content);
            if (announcement.private) $("#annpvt-1").prop("checked", true);
            else $("#annpvt-0").prop("checked", true);
            $('#annselect option:eq(' + announcement.atype + ')').prop('selected', true);
        },
        error: function (data) {
            $("#fetchAnnouncementBtn").html("Fetch Data");
            $("#fetchAnnouncementBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(
                `Failed to fetch announcement. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })

}

function NewAnn() {
    anntype = parseInt($("#annselect").find(":selected").val());
    title = $("#anntitle").val();
    content = $("#anncontent").val();
    annid = $("#annid").val();
    pvt = $("#annpvt-1").prop("checked");
    chnid = $("#annchan").val().replaceAll(" ", "");

    if (chnid != "" && !isNumber(chnid)) {
        toastFactory("warning", "Error", "Channel ID must be an integar if specified!", 5000, false);
        return;
    }

    GeneralLoad();
    $("#newAnnBtn").html("Working...");
    $("#newAnnBtn").attr("disabled", "disabled");

    op = "create";
    if (isNumber(annid)) {
        if (title != "" || content != "") {
            op = "update";
        } else {
            op = "delete";
        }
    }

    if (op == "update") {
        annid = parseInt(annid);
        $.ajax({
            url: "https://drivershub.charlws.com/atm/announcement",
            type: "PATCH",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + token
            },
            data: {
                "aid": annid,
                "title": title,
                "content": content,
                "atype": anntype,
                "pvt": pvt,
                "channelid": chnid
            },
            success: function (data) {
                // Un-disable the submit button
                $("#newAnnBtn").prop("disabled", false);
                $("#newAnnBtn").html("Submit");
                if (data.error == false) {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Success',
                        text: 'Announcement updated! Refresh page to view it!',
                        icon: 'success',
                        confirmButtonText: 'OK'
                    })
                } else {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Error',
                        text: data.descriptor ? data.descriptor : 'Unknown Error',
                        icon: 'error',
                        confirmButtonText: 'OK'
                    })
                    console.warn(`Announcement update failed: ${data.descriptor ? data.descriptor : 'Unknown error'}`);
                    console.log(data);
                }
            },
            error: function (data) {
                // Un-disable the submit button
                $("#newAnnBtn").prop("disabled", false);
                $("#newAnnBtn").html("Submit");

                // Trigger req swal.fire
                Swal.fire({
                    title: 'Error',
                    text: data.descriptor ? data.descriptor : 'Unknown Error',
                    icon: 'error',
                    confirmButtonText: 'OK'
                })

                console.warn(`Announcement update failed: ${data.descriptor ? data.descriptor : 'Unknown error'}`);
                console.log(data);
            }
        });
    } else if (op == "create") {
        $.ajax({
            url: "https://drivershub.charlws.com/atm/announcement",
            type: "POST",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + token
            },
            data: {
                "title": title,
                "content": content,
                "atype": anntype,
                "pvt": pvt,
                "channelid": chnid
            },
            success: function (data) {
                // Un-disable the submit button
                $("#newAnnBtn").prop("disabled", false);
                $("#newAnnBtn").html("Submit");
                if (data.error == false) {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Success',
                        text: 'Announcement created! Refresh page to view it!',
                        icon: 'success',
                        confirmButtonText: 'OK'
                    })
                } else {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Error',
                        text: data.descriptor ? data.descriptor : 'Unknown Error',
                        icon: 'error',
                        confirmButtonText: 'OK'
                    })

                    console.warn(
                        `Announcement creation failed: ${data.descriptor ? data.descriptor : 'Unknown error'}`);
                    console.log(data);
                }
            },
            error: function (data) {
                // Un-disable the submit button
                $("#newAnnBtn").prop("disabled", false);
                $("#newAnnBtn").html("Submit");

                // Trigger req swal.fire
                Swal.fire({
                    title: 'Error',
                    text: data.descriptor ? data.descriptor : 'Unknown Error',
                    icon: 'error',
                    confirmButtonText: 'OK'
                })

                console.warn(`Announcement creation failed: ${data.descriptor ? data.descriptor : 'Unknown error'}`);
                console.log(data);
            }
        });
    } else if (op == "delete") {
        annid = parseInt(annid);
        $.ajax({
            url: "https://drivershub.charlws.com/atm/announcement?aid=" + annid,
            type: "DELETE",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + token
            },
            success: function (data) {
                // Un-disable the submit button
                $("#newAnnBtn").prop("disabled", false);
                $("#newAnnBtn").html("Submit");
                if (data.error == false) {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Success',
                        text: 'Announcement deleted!',
                        icon: 'success',
                        confirmButtonText: 'OK'
                    })
                } else {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Error',
                        text: data.descriptor ? data.descriptor : 'Unknown Error',
                        icon: 'error',
                        confirmButtonText: 'OK'
                    })
                }
            },
            error: function (data) {
                // Un-disable the submit button
                $("#newAnnBtn").prop("disabled", false);
                $("#newAnnBtn").html("Submit");

                // Trigger req swal.fire
                Swal.fire({
                    title: 'Error',
                    text: data.descriptor ? data.descriptor : 'Unknown Error',
                    icon: 'error',
                    confirmButtonText: 'OK'
                })

                console.warn(`Announcement deletion failed: ${data.descriptor ? data.descriptor : 'Unknown error'}`);
                console.log(data);
            }
        });
    }
}

function FetchEvent(showdetail = -1) {
    eventid = $("#eventid").val();
    if (!isNumber(eventid)) {
        return toastFactory("error", "Error", "Event ID must be in integar!", 5000, false);
    }

    GeneralLoad();
    $("#fetchEventBtn").html("Working...");
    $("#fetchEventBtn").attr("disabled", "disabled");

    $.ajax({
        url: "https://drivershub.charlws.com/atm/event?eventid=" + eventid,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#fetchEventBtn").html("Fetch Data");
            $("#fetchEventBtn").removeAttr("disabled");

            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);

            const event = data.response;
            allevents[event.eventid] = event;
            $("#eventtitle").val(event.title);
            $("#eventtmplink").val(event.tmplink);
            $("#eventfrom").val(event.departure);
            $("#eventto").val(event.destination);
            $("#eventdistance").val(event.distance);
            offset = (+new Date().getTimezoneOffset()) * 60 * 1000;
            $("#eventmts").val(new Date(event.mts * 1000 - offset).toISOString().substring(0, 16));
            $("#eventdts").val(new Date(event.dts * 1000 - offset).toISOString().substring(0, 16));
            imgs = "";
            for (let i = 0; i < event.img.length; i++) {
                imgs += event.img[i] + "\n";
            }
            if (event.private) $("#eventpvt-1").prop("checked", true);
            else $("#eventpvt-0").prop("checked", true);
            $("#eventimgs").val(imgs);

            if (showdetail != -1) eventDetail(showdetail);
        },
        error: function (data) {
            $("#fetchEventBtn").html("Fetch Data");
            $("#fetchEventBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(
                `Failed to fetch event. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function FetchEventAttendee() {
    eventid = $("#aeventid").val();
    if (!isNumber(eventid)) {
        return toastFactory("error", "Error", "Event ID must be in integar!", 5000, false);
    }

    GeneralLoad();
    $("#fetchEventAttendeeBtn").html("Working...");
    $("#fetchEventAttendeeBtn").attr("disabled", "disabled");

    $.ajax({
        url: "https://drivershub.charlws.com/atm/event?eventid=" + eventid,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#fetchEventAttendeeBtn").html("Fetch Existing Attendees");
            $("#fetchEventAttendeeBtn").removeAttr("disabled");

            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);

            const event = data.response;
            attendeeids = event.attendeeid.split(",");
            attendeenames = event.attendee.split(",");
            $(".attendee").remove();
            for (let i = 0; i < attendeeids.length; i++) {
                userid = attendeeids[i];
                username = attendeenames[i];
                if (userid == "") continue;
                $("#attendeeId").before(`<span class='tag attendee' id='attendeeid-${userid}'>${username} (${userid})
                <a style='cursor:pointer' onclick='$("#attendeeid-${userid}").remove()'><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x" viewBox="0 0 16 16"> <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/> </svg> </a></span>`);
            }
        },
        error: function (data) {
            $("#fetchEventAttendeeBtn").html("Fetch Existing Attendees");
            $("#fetchEventAttendeeBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(
                `Failed to fetch event attendees. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function UpdateEventAttendees() {
    eventid = $("#aeventid").val();
    if (!isNumber(eventid)) {
        return toastFactory("error", "Error", "Event ID must be in integar!", 5000, false);
    }
    attendeeid = "";
    $(".attendee").each(function (index, value) {
        attendeeid += $(value).prop('id').replaceAll("attendeeid-", "") + ",";
    })
    attendeeid = attendeeid.substring(0, attendeeid.length - 1);
    points = $("#attendeePoints").val();
    if (!isNumber(points)) {
        return toastFactory("error", "Error", "Points must be in integar!", 5000, false);
    }

    GeneralLoad();
    $("#attendeeBtn").html("Working...");
    $("#attendeeBtn").attr("disabled", "disabled");

    $.ajax({
        url: "https://drivershub.charlws.com/atm/event/attendee",
        type: "POST",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        data: {
            "eventid": eventid,
            "attendees": attendeeid,
            "points": points
        },
        success: function (data) {
            $("#attendeeBtn").html("Update");
            $("#attendeeBtn").removeAttr("disabled");

            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            loadEvent();
            Swal.fire({
                title: 'Event Attendees Updated!',
                html: "<p style='text-align:left'>" + data.response.message.replaceAll("\n", "<br>") + "</p>",
                icon: 'success',
                confirmButtonText: 'OK'
            })
        },
        error: function (data) {
            $("#attendeeBtn").html("Update");
            $("#attendeeBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(
                `Failed to update event attendees. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })

}

function NewEvent() {
    title = $("#eventtitle").val();
    tmplink = $("#eventtmplink").val();
    from = $("#eventfrom").val();
    to = $("#eventto").val();
    distance = $("#eventdistance").val();
    mts = +new Date($("#eventmts").val());
    dts = +new Date($("#eventdts").val());
    mts /= 1000;
    dts /= 1000;
    eventid = $("#eventid").val();
    pvt = $("#eventpvt-1").prop("checked");
    img = $("#eventimgs").val().replaceAll("\n", ",");

    GeneralLoad();
    $("#newEventBtn").html("Working...");
    $("#newEventBtn").attr("disabled", "disabled");

    op = "create";
    if (isNumber(eventid)) {
        if (title != "" || from != "" || to != "" || distance != "") {
            op = "update";
        } else {
            op = "delete";
        }
    }

    if (op == "update") {
        eventid = parseInt(eventid);
        $.ajax({
            url: "https://drivershub.charlws.com/atm/event",
            type: "PATCH",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + token
            },
            data: {
                "eventid": eventid,
                "title": title,
                "tmplink": tmplink,
                "departure": from,
                "destination": to,
                "distance": distance,
                "mts": mts,
                "dts": dts,
                "img": img,
                "pvt": pvt
            },
            success: function (data) {
                // Un-disable the submit button
                $("#newEventBtn").prop("disabled", false);
                $("#newEventBtn").html("Submit");
                if (data.error == false) {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Success',
                        text: 'Event updated!',
                        icon: 'success',
                        confirmButtonText: 'OK'
                    })
                    loadEvent();
                } else {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Error',
                        text: data.descriptor ? data.descriptor : 'Unknown Error',
                        icon: 'error',
                        confirmButtonText: 'OK'
                    })
                    console.warn(`Event update failed: ${data.descriptor ? data.descriptor : 'Unknown error'}`);
                    console.log(data);
                }
            },
            error: function (data) {
                // Un-disable the submit button
                $("#newEventBtn").prop("disabled", false);
                $("#newEventBtn").html("Submit");

                // Trigger req swal.fire
                Swal.fire({
                    title: 'Error',
                    text: data.descriptor ? data.descriptor : 'Unknown Error',
                    icon: 'error',
                    confirmButtonText: 'OK'
                })

                console.warn(`Event update failed: ${data.descriptor ? data.descriptor : 'Unknown error'}`);
                console.log(data);
            }
        });
    } else if (op == "create") {
        $.ajax({
            url: "https://drivershub.charlws.com/atm/event",
            type: "POST",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + token
            },
            data: {
                "title": title,
                "tmplink": tmplink,
                "departure": from,
                "destination": to,
                "distance": distance,
                "mts": mts,
                "dts": dts,
                "img": img,
                "pvt": pvt
            },
            success: function (data) {
                // Un-disable the submit button
                $("#newEventBtn").prop("disabled", false);
                $("#newEventBtn").html("Submit");
                if (data.error == false) {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Success',
                        text: 'Event created!',
                        icon: 'success',
                        confirmButtonText: 'OK'
                    })
                    loadEvent();
                } else {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Error',
                        text: data.descriptor ? data.descriptor : 'Unknown Error',
                        icon: 'error',
                        confirmButtonText: 'OK'
                    })

                    console.warn(
                        `Event creation failed: ${data.descriptor ? data.descriptor : 'Unknown error'}`);
                    console.log(data);
                }
            },
            error: function (data) {
                // Un-disable the submit button
                $("#newEventBtn").prop("disabled", false);
                $("#newEventBtn").html("Submit");

                // Trigger req swal.fire
                Swal.fire({
                    title: 'Error',
                    text: data.descriptor ? data.descriptor : 'Unknown Error',
                    icon: 'error',
                    confirmButtonText: 'OK'
                })

                console.warn(`Event creation failed: ${data.descriptor ? data.descriptor : 'Unknown error'}`);
                console.log(data);
            }
        });
    } else if (op == "delete") {
        annid = parseInt(annid);
        $.ajax({
            url: "https://drivershub.charlws.com/atm/event?eventid=" + eventid,
            type: "DELETE",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + token
            },
            success: function (data) {
                // Un-disable the submit button
                $("#newEventBtn").prop("disabled", false);
                $("#newEventBtn").html("Submit");
                if (data.error == false) {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Success',
                        text: 'Event deleted!',
                        icon: 'success',
                        confirmButtonText: 'OK'
                    })
                    loadEvent();
                } else {
                    // Trigger req swal.fire
                    Swal.fire({
                        title: 'Error',
                        text: data.descriptor ? data.descriptor : 'Unknown Error',
                        icon: 'error',
                        confirmButtonText: 'OK'
                    })
                }
            },
            error: function (data) {
                // Un-disable the submit button
                $("#newEventBtn").prop("disabled", false);
                $("#newEventBtn").html("Submit");

                // Trigger req swal.fire
                Swal.fire({
                    title: 'Error',
                    text: data.descriptor ? data.descriptor : 'Unknown Error',
                    icon: 'error',
                    confirmButtonText: 'OK'
                })

                console.warn(`Event deletion failed: ${data.descriptor ? data.descriptor : 'Unknown error'}`);
                console.log(data);
            }
        });
    }
}

function SubmitApp() {
    apptype = $("#appselect").find(":selected").text();
    data = "";
    if (apptype == "Driver") {
        apptype = 1;

        q1 = $("#da-q1").val();
        q2 = $("#da-q2").val();
        q3 = $("#da-q3").val();
        q4 = $("#da-q4").val();


        // Check if any of the fields are empty
        if (q1 == "" || q2 == "" || q3 == "" || q4 == "") {
            toastFactory("warning", "Error", "You must fill in all the fields!", 5000, false);
            return;
        }


        // Checks for is in vtc and terms
        if ($("#in-another-vtc").prop("checked")) {
            toastFactory("warning", "Error", "You can only be in one VTC at a time!", 5000, false);
            return;
        }

        if (!$("#da-agree").prop("checked")) {
            toastFactory("warning", "Error", "You must agree to the terms and conditions!", 5000, false);
            return;
        }

        // Check if q1 is a vaild date
        const birthDate = new Date(q1);

        if (isNaN(birthDate.getTime())) {
            toastFactory("warning", "Error", "You must enter a valid date!", 5000, false);
            return;
        }

        // Check that q1 follows the MM/DD/YYYY format
        if (q1.length != 10) {
            toastFactory("warning", "Error", "You must enter a date in the MM/DD/YYYY format!", 5000, false);
            return;
        }

        // Check if they are at least 13 years old
        const today = new Date();

        if (today.getFullYear() - birthDate.getFullYear() < 13) {
            toastFactory("warning", "Error", "You must be at least 13 years old to apply!", 5000, false);
            return;
        }

        data = {
            "Birthday": q1,
            "How did you find us?": q2,
            "What are your interests?": q3,
            "Why do you want to be a part our VTC?": q4
        };
    } else if (apptype == "Staff") {
        apptype = 2;

        q1 = $("#sa-q1").val();
        q2 = $("#sa-q2").val();
        q3 = $("#sa-q3").val();
        q4 = $("#sa-q4").val();
        q5 = $("#sa-q5").val();
        pos = $("#sa-select").find(":selected").text();

        // Check if any of the fields are empty
        if (q1 == "" || q2 == "" || q3 == "" || q4 == "" || q5 == "") {
            toastFactory("warning", "Error", "You must fill in all the fields!", 5000, false);
            return;
        }

        if (!$("#sa-agree").prop("checked")) {
            toastFactory("warning", "Error", "You must agree to the terms and conditions!", 5000, false);
            return;
        }


        data = {
            "Applying For": pos,
            "Birthday": q1,
            "Country & Time Zone": q2,
            "Summary": q3,
            "Why are you interested in joining the position you are applying for? What do you want to achieve?": q4,
            "Do you have a lot of time to dedicate to this position? ": q5
        }
    } else if (apptype == "LOA") {
        apptype = 3;
        q1 = $("#la-q1").val();
        q2 = $("#la-q2").val();
        q3 = $("#la-q3").val();
        q4 = $("#la-leave").find(":selected").text();

        // Check if any of the fields are empty
        if (q1 == "" || q2 == "" || q3 == "") {
            toastFactory("warning", "Error", "You must fill in all the fields!", 5000, false);
            return;
        }

        data = {
            "Start Date": q1,
            "End Date": q2,
            "Reason": q3,
            "Will they leave position or leave VTC?": q4
        }
    }
    data = JSON.stringify(data);

    // After we've reached here, change the submit button text to "Submitting..."
    $("#submitAppBttn").html("Submitting...");

    // Disable the submit button
    $("#submitAppBttn").attr("disabled", "disabled");

    $.ajax({
        url: "https://drivershub.charlws.com/atm/application",
        type: "POST",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + token
        },
        data: {
            "apptype": apptype,
            "data": data
        },
        success: function (data) {
            if (data.error == false) {
                // Un-disable the submit button
                $("#submitAppBttn").prop("disabled", false);
                $("#submitAppBttn").html("Submit");

                // Trigger req swal.fire
                Swal.fire({
                    title: 'Success',
                    text: 'Your application has been submitted! Best of luck!',
                    icon: 'success',
                    confirmButtonText: 'OK'
                })
            } else {
                // Un-disable the submit button
                $("#submitAppBttn").prop("disabled", false);
                $("#submitAppBttn").html("Submit");

                // Trigger req swal.fire
                Swal.fire({
                    title: 'Error',
                    text: `${data.descriptor}`,
                    icon: 'error',
                    confirmButtonText: 'OK'
                })
            }
        },
        error: function (data) {
            // Un-disable the submit button
            $("#submitAppBttn").prop("disabled", false);
            $("#submitAppBttn").html("Submit");

            // Trigger req swal.fire
            Swal.fire({
                title: 'Error',
                text: `ERROR_UNHANDLED`,
                icon: 'error',
                confirmButtonText: 'OK'
            })

            console.warn('Failed to submit application (Unhandled Error): ', data.descriptor ? data.descriptor :
                'No Error Descriptor - check cors?');
        }
    });
}

function ShowStaffTabs() {
    roles = JSON.parse(localStorage.getItem("roles"));
    name = localStorage.getItem("name");
    avatar = localStorage.getItem("avatar");
    discordid = localStorage.getItem("discordid");
    highestrole = localStorage.getItem("highestrole");
    if (highestrole == undefined || highestrole == "undefined") highestrole = "Loner";
    $("#name").html(name);
    $("#role").html(highestrole);
    if (avatar != null) {
        if (avatar.startsWith("a_"))
            $("#avatar").attr("src", "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif");
        else
            $("#avatar").attr("src", "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png");
    } else {
        avatar = "/images/atm-black.png";
    }
    isEM = false;
    $("#StaffAnnTabBtn").hide();
    if (roles != null && roles != undefined) {
        highestrole = 99999;
        for (i = 0; i < roles.length; i++) {
            if (roles[i] < highestrole) {
                highestrole = roles[i];
            }
            if (roles[i] == 40 || roles[i] == 41) {
                if (roles[i] == 40) isEM = true;
                $("#StaffAnnTabBtn").show(); // event staff
                $("#StaffEventBtn").show(); // event staff
                $("#eventattendee").show();
                setInterval(function () {
                    title = $("#anntitle").val();
                    content = $("#anncontent").val();
                    annid = $("#annid").val();
                    if (isNumber(annid)) {
                        if (title != "" || content != "") {
                            $("#newAnnBtn").html("Update Announcement");
                            $("#newAnnBtn").css("background-color", "lightgreen");
                        } else {
                            $("#newAnnBtn").html("Delete Announcement");
                            $("#newAnnBtn").css("background-color", "red");
                        }
                    } else {
                        $("#newAnnBtn").html("Create Announcement");
                        $("#newAnnBtn").css("background-color", "blue");
                    }
                });
                setInterval(function () {
                    title = $("#eventtitle").val();
                    from = $("#eventfrom").val();
                    to = $("#eventto").val();
                    distance = $("#eventdistance").val();
                    mts = $("#eventmts").val();
                    dts = $("#eventdts").val();
                    eventid = $("#eventid").val();
                    if (isNumber(eventid)) {
                        if (title != "" || from != "" || to != "" || distance != "" || mts != "" || dts != "") {
                            $("#newEventBtn").html("Update Event");
                            $("#newEventBtn").css("background-color", "lightgreen");
                        } else {
                            $("#newEventBtn").html("Delete Event");
                            $("#newEventBtn").css("background-color", "red");
                        }
                    } else {
                        $("#newEventBtn").html("Create Event");
                        $("#newEventBtn").css("background-color", "blue");
                    }
                });
            }
        }
        if (highestrole < 100) {
            $("#stafftabs").show();
            if (highestrole >= 30) {
                $("#AllAppBtn").hide();
                $("#StaffMembersBtn").hide();
            } else {
                $("#StaffMembersBtn").show();
                $("#AllAppBtn").show();
            }
        }
        if (highestrole <= 10) {
            $("#updateStaffPos").show();
            $("#StaffAnnTabBtn").show();
            $("#StaffEventBtn").show(); // event staff
            $("#eventattendee").show();
            setInterval(function () {
                title = $("#anntitle").val();
                content = $("#anncontent").val();
                annid = $("#annid").val();
                if (isNumber(annid)) {
                    if (title != "" || content != "") {
                        $("#newAnnBtn").html("Update Announcement");
                        $("#newAnnBtn").css("background-color", "lightgreen");
                    } else {
                        $("#newAnnBtn").html("Delete Announcement");
                        $("#newAnnBtn").css("background-color", "red");
                    }
                } else {
                    $("#newAnnBtn").html("Create Announcement");
                    $("#newAnnBtn").css("background-color", "blue");
                }
            });
            setInterval(function () {
                title = $("#eventtitle").val();
                from = $("#eventfrom").val();
                to = $("#eventto").val();
                distance = $("#eventdistance").val();
                mts = $("#eventmts").val();
                dts = $("#eventdts").val();
                eventid = $("#eventid").val();
                if (isNumber(eventid)) {
                    if (title != "" || from != "" || to != "" || distance != "" || mts != "" || dts != "") {
                        $("#newEventBtn").html("Update Event");
                        $("#newEventBtn").css("background-color", "lightgreen");
                    } else {
                        $("#newEventBtn").html("Delete Event");
                        $("#newEventBtn").css("background-color", "red");
                    }
                } else {
                    $("#newEventBtn").html("Create Event");
                    $("#newEventBtn").css("background-color", "blue");
                }
            });
        }
    }
}

function validate() {
    token = localStorage.getItem("token");
    userid = localStorage.getItem("userid");
    if (token == "guest") {
        $("#header").prepend(
            "<p style='color:orange'>Guest Mode - <a style='color:grey' href='/login'>Login</a></p>");
        return;
    }
    if (userid != -1 && isNumber(userid)) {
        $("#memberOnlyTabs").show();
    }
    $("#recruitment").show();
    $.ajax({
        url: "https://drivershub.charlws.com/atm/user/validate",
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + token
        },
        success: function (data) {
            if (data.error) {
                localStorage.removeItem("token");
                window.location.href = "/login";
            }
            if (data.response.extra == "steamauth") {
                $("#header").prepend(
                    "<p style='color:orange'>Steam not bound! You must bind it to become a member! <a style='color:grey' href='/auth'>Click here to bind it</a></p>");
            } else if (data.response.extra == "truckersmp") {
                $("#header").prepend(
                    "<p style='color:orange'>TruckersMP not bound! You must bind it to become a member! <a style='color:grey' href='/auth'>Click here to bind it</a></p>");
            } else {
                color = "green";
                if (isdark) color = "lightgreen";
                $("#header").prepend(`<p style="color:${color}"><svg style="color:${color};display:inline" xmlns="http://www.w3.org/2000/svg" width="18" height="18"
                fill="currentColor" class="bi bi-activity" viewBox="0 0 16 16">
                <path fill-rule="evenodd"
                  d="M6 2a.5.5 0 0 1 .47.33L10 12.036l1.53-4.208A.5.5 0 0 1 12 7.5h3.5a.5.5 0 0 1 0 1h-3.15l-1.88 5.17a.5.5 0 0 1-.94 0L6 3.964 4.47 8.171A.5.5 0 0 1 4 8.5H.5a.5.5 0 0 1 0-1h3.15l1.88-5.17A.5.5 0 0 1 6 2Z"
                  fill="${color}"></path>
              </svg>&nbsp;&nbsp;<span id="livedriver2" style="color:${color}"></span></p>`);
            }
        }
    });
    $.ajax({
        url: "https://drivershub.charlws.com/atm/user/info",
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + token
        },
        success: function (data) {
            if (data.error == false) {
                localStorage.setItem("roles", JSON.stringify(data.response.roles));
                localStorage.setItem("name", data.response.name);
                localStorage.setItem("avatar", data.response.avatar);
                localStorage.setItem("discordid", data.response.discordid);
                localStorage.setItem("userid", data.response.userid);
                userid = data.response.userid;
                if (data.response.userid != -1) {
                    $("#AllMemberBtn").show();
                }
                roles = data.response.roles.sort().reverse();
                highestrole = roles[0];
                ShowStaffTabs();
                name = data.response.name;
                avatar = data.response.avatar;
                discordid = data.response.discordid;
                $("#name").html(name);
                if (avatar.startsWith("a_"))
                    $("#avatar").attr("src", "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif");
                else
                    $("#avatar").attr("src", "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png");

                rolesLastUpdate = localStorage.getItem("rolesLastUpdate");
                if (rolesLastUpdate == null || rolesLastUpdate == undefined || parseInt(rolesLastUpdate) < (+new Date() - 86400)) {
                    $.ajax({
                        url: "https://drivershub.charlws.com/atm/member/roles",
                        type: "GET",
                        dataType: "json",
                        success: function (data) {
                            rolelist = data.response;
                            rolestxt = [];
                            for (i = 0; i < roles.length; i++) {
                                rolestxt.push(rolelist[roles[i]]);
                            }
                            hrole = rolestxt[0];
                            for (i = 0; i < rolestxt.length && highestrole >= 10; i++) {
                                if (rolestxt[i].indexOf("Manager") != -1 || rolestxt[i].indexOf("Lead") != -1) {
                                    hrole = rolestxt[i];
                                    break;
                                }
                            }
                            localStorage.setItem("highestrole", hrole);
                            localStorage.setItem("rolelist", JSON.stringify(rolelist));
                            localStorage.setItem("rolesLastUpdate", (+new Date()).toString());
                            if (hrole == undefined || hrole == "undefined") hrole = "Loner";
                            $("#role").html(hrole);
                            roleids = Object.keys(rolelist);
                            for (var i = 0; i < roleids.length; i++) {
                                if (roleids[i] <= highestrole)
                                    $("#rolelist").append(`<li><input disabled type="checkbox" id="role` + roleids[i] +
                                        `" name="assignrole" value="role` + roleids[i] + `">
    <label for="role` + roleids[i] + `">` + rolelist[roleids[i]] + `</label></li>`);
                                else
                                    $("#rolelist").append(`<li><input type="checkbox" id="role` + roleids[i] +
                                        `" name="assignrole" value="role` + roleids[i] + `">
    <label for="role` + roleids[i] + `">` + rolelist[roleids[i]] + `</label></li>`);
                            }
                        }
                    });
                } else {
                    rolestxt = [];
                    for (i = 0; i < roles.length; i++) {
                        rolestxt.push(rolelist[roles[i]]);
                    }
                    hrole = rolestxt[0];
                    for (i = 0; i < rolestxt.length && highestrole >= 10; i++) {
                        if (rolestxt[i].indexOf("Manager") != -1 || rolestxt[i].indexOf("Lead") != -1) {
                            hrole = rolestxt[i];
                            break;
                        }
                    }
                    localStorage.setItem("highestrole", hrole);
                    if (hrole == undefined || hrole == "undefined") hrole = "Loner";
                    $("#role").html(hrole);
                    roleids = Object.keys(rolelist);
                    for (var i = 0; i < roleids.length; i++) {
                        if (roleids[i] <= highestrole)
                            $("#rolelist").append(`<li><input disabled type="checkbox" id="role` + roleids[i] +
                                `" name="assignrole" value="role` + roleids[i] + `">
<label for="role` + roleids[i] + `">` + rolelist[roleids[i]] + `</label></li>`);
                        else
                            $("#rolelist").append(`<li><input type="checkbox" id="role` + roleids[i] +
                                `" name="assignrole" value="role` + roleids[i] + `">
<label for="role` + roleids[i] + `">` + rolelist[roleids[i]] + `</label></li>`);
                    }
                }
                if (userid != -1) {
                    $.ajax({
                        url: "https://drivershub.charlws.com/atm/member/info?userid=" + userid,
                        type: "GET",
                        dataType: "json",
                        headers: {
                            "Authorization": "Bearer " + token
                        },
                        success: function (data) {
                            if (data.error == false) {
                                d = data.response;
                                points = parseInt(d.distance / 1.6 + d.eventpnt);
                                rank = point2rank(points);
                                $("#ranktotpoints").html(TSeparator(points) + " - " + rank);
                                if ($("#role").html() == "Driver")
                                    $("#role").html(rank);
                            }
                        }
                    });
                }
            }
        }
    });
}

function loadLeaderboard(recurse = true) {
    page = parseInt($("#lpages").val())
    if (page == "") page = 1;
    if (page == undefined) page = 1;
    GeneralLoad();
    $("#loadLeaderboardBtn").html("...");
    $("#loadLeaderboardBtn").attr("disabled", "disabled");
    starttime = -1;
    endtime = -1;
    if ($("#lbstart").val() != "" && $("#lbend").val() != "") {
        starttime = +new Date($("#lbstart").val()) / 1000;
        endtime = +new Date($("#lbend").val()) / 1000;
    }
    speedlimit = parseInt($("#lbspeedlimit").val());
    if (!isNumber(speedlimit)) {
        speedlimit = 0;
    } else {
        speedlimit *= 1.6;
    }
    $.ajax({
        url: "https://drivershub.charlws.com/atm/dlog/leaderboard?page=" + page + "&speedlimit=" + parseInt(speedlimit) + "&starttime=" + starttime + "&endtime=" + endtime,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#loadLeaderboardBtn").html("Go");
            $("#loadLeaderboardBtn").removeAttr("disabled");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            $("#leaderboardTable").empty();
            const leaderboard = data.response.list;

            if (leaderboard.length == 0) {
                $("#leaderboardTableHead").hide();
                $("#leaderboardTable").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                $("#lpages").val(1);
                if (recurse) loadLeaderboard(recurse = false);
                return;
            }
            $("#leaderboardTableHead").show();
            totpage = Math.ceil(data.response.tot / 10);
            if (page > totpage) {
                $("#lpages").val(1);
                if (recurse) loadLeaderboard(recurse = false);
                return;
            }
            if (page <= 0) {
                $("#lpages").val(1);
                page = 1;
            }
            $("#ltotpages").html(totpage);
            $("#leaderboardTableControl").children().remove();
            $("#leaderboardTableControl").append(`
            <button type="button" style="display:inline"
            class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
            onclick="$('#lpages').val(1);loadLeaderboard();">1</button>`);
            if (page > 3) {
                $("#leaderboardTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            for (var i = Math.max(page - 1, 2); i <= Math.min(page + 1, totpage - 1); i++) {
                $("#leaderboardTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#lpages').val(${i});loadLeaderboard();">${i}</button>`);
            }
            if (page < totpage - 2) {
                $("#leaderboardTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            if (totpage > 1) {
                $("#leaderboardTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#lpages').val(${totpage});loadLeaderboard();">${totpage}</button>`);
            }

            for (i = 0; i < leaderboard.length; i++) {
                user = leaderboard[i];
                userid = user.userid;
                name = user.name;
                distance = TSeparator(parseInt(user.distance / 1.6));
                discordid = user.discordid;
                avatar = user.avatar;
                totalpnt = TSeparator(parseInt(user.totalpnt));
                if (avatar != null) {
                    if (avatar.startsWith("a_"))
                        src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif";
                    else
                        src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png";
                } else {
                    avatar = "/images/atm-black.png";
                }
                console.log(user.totnolimit);
                $("#leaderboardTable").append(`<tr class="text-xs">
              <td class="py-5 px-6 font-medium">
                <a style="cursor: pointer" onclick="loadProfile(${userid})"><img src='${src}' width="20px" style="display:inline;border-radius:100%"> ${name}</a></td>
                <td class="py-5 px-6">${point2rank(user.totnolimit)}</td>
                <td class="py-5 px-6">${distance}</td>
                <td class="py-5 px-6">${user.eventpnt}</td>
              <td class="py-5 px-6">${totalpnt}</td>
            </tr>`);
            }
        },
        error: function (data) {
            $("#loadLeaderboardBtn").html("Go");
            $("#loadLeaderboardBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(
                `Failed to load leaderboard. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function requestRole() {
    GeneralLoad();
    $("#requestRoleBtn").html("Working...");
    $("#requestRoleBtn").attr("disabled", "disabled");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/member/discordrole",
        type: "PATCH",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#requestRoleBtn").html("Request Role");
            $("#requestRoleBtn").removeAttr("disabled");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            else return toastFactory("success", "Success", "You have got your new role!", 5000, false);
        },
        error: function (data) {
            $("#loadLeaderboardBtn").html("Go");
            $("#loadLeaderboardBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(
                `Failed to load leaderboard. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function loadDelivery(recurse = true) {
    page = parseInt($("#dpages").val())
    if (page == "") page = 1;
    if (page == undefined) page = 1;
    GeneralLoad();
    $("#loadDeliveryBtn").html("...");
    $("#loadDeliveryBtn").attr("disabled", "disabled");
    starttime = -1;
    endtime = -1;
    if ($("#dstart").val() != "" && $("#dend").val() != "") {
        starttime = +new Date($("#dstart").val()) / 1000;
        endtime = +new Date($("#dend").val()) / 1000;
    }
    speedlimit = parseInt($("#dspeedlimit").val());
    if (!isNumber(speedlimit)) {
        speedlimit = 0;
    } else {
        speedlimit *= 1.6;
    }
    $.ajax({
        url: "https://drivershub.charlws.com/atm/dlog/list?page=" + page + "&speedlimit=" + parseInt(speedlimit) + "&starttime=" + starttime + "&endtime=" + endtime,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#loadDeliveryBtn").html("Go");
            $("#loadDeliveryBtn").removeAttr("disabled");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            $("#deliveryTable").empty();
            const deliveries = data.response.list;

            if (deliveries.length == 0) {
                $("#deliveryTableHead").hide();
                $("#deliveryTable").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                $("#dpages").val(1);
                if (recurse) loadDelivery(recurse = false);
                return;
            }
            $("#deliveryTableHead").show();
            totpage = Math.ceil(data.response.tot / 10);
            if (page > totpage) {
                $("#dpages").val(1);
                if (recurse) loadDelivery(recurse = false);
                return;
            }
            if (page <= 0) {
                $("#dpages").val(1);
                page = 1;
            }
            $("#dtotpages").html(totpage);
            $("#deliveryTableControl").children().remove();
            $("#deliveryTableControl").append(`
            <button type="button" style="display:inline"
            class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
            onclick="$('#dpages').val(1);loadDelivery();">1</button>`);
            if (page > 3) {
                $("#deliveryTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            for (var i = Math.max(page - 1, 2); i <= Math.min(page + 1, totpage - 1); i++) {
                $("#deliveryTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#dpages').val(${i});loadDelivery();">${i}</button>`);
            }
            if (page < totpage - 2) {
                $("#deliveryTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            if (totpage > 1) {
                $("#deliveryTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#dpages').val(${totpage});loadDelivery();">${totpage}</button>`);
            }

            for (i = 0; i < deliveries.length; i++) {
                const delivery = deliveries[i];
                // Fill the table using this format: 
                // <tr class="text-xs">
                //  <td class="py-5 px-6 font-medium">id here</td>
                //    <td class="py-5 px-6 font-medium">name here</td>
                //  </tr>
                //
                distance = TSeparator(parseInt(delivery.distance / 1.6));
                cargo_mass = parseInt(delivery.cargo_mass / 1000);
                unittxt = "€";
                if (delivery.unit == 2) unittxt = "$";
                profit = TSeparator(delivery.profit);
                color = "";
                if (delivery.profit < 0) color = "grey";
                dtl = "";
                if (localStorage.getItem("token") != "guest") {
                    dtl =
                        `<td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:grey" id="DeliveryInfoBtn${delivery.logid}" onclick="deliveryDetail('${delivery.logid}')">Show Details</td>`;
                }
                $("#deliveryTable").append(`
            <tr class="text-xs" style="color:${color}">
              <td class="py-5 px-6 font-medium">${delivery.logid}</td>
              <td class="py-5 px-6 font-medium"><a style='cursor:pointer' onclick='loadProfile(${delivery.userid})'>${delivery.name}</a></td>
              <td class="py-5 px-6 font-medium">${delivery.source_company}, ${delivery.source_city}</td>
              <td class="py-5 px-6 font-medium">${delivery.destination_company}, ${delivery.destination_city}</td>
              <td class="py-5 px-6 font-medium">${distance}Mi</td>
              <td class="py-5 px-6 font-medium">${delivery.cargo} (${cargo_mass}t)</td>
              <td class="py-5 px-6 font-medium">${unittxt}${profit}</td>
              ${dtl}
            </tr>`);
            }
        },
        error: function (data) {
            $("#loadDeliveryBtn").html("Go");
            $("#loadDeliveryBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(
                `Failed to load delivery log. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

deliveryRoute = [];
rri = 0;
rrspeed = 20;
rrevents = [];
punit = "€";
curlogid = -1;
async function deliveryRoutePlay() {
    if (window.dn == undefined || window.dn.previousExtent_ == undefined) return toastFactory("error", "Error:", "Please zoom & drag the map to activate it.", 5000, false);
    clearInterval(dmapint);
    dmapint = -999;
    window.mapcenter["dmap"] = [deliveryRoute[0][0], -deliveryRoute[0][1]];
    prew = 0;
    preh = 0;
    pred = 0;
    pret = 0;
    for (; rri < deliveryRoute.length; rri += Math.max(rrspeed - 50, 1)) {
        if (rrspeed <= 0) rrspeed = 1;
        if (rri < 0) rri = 0;
        if (rri >= deliveryRoute.length) rri = deliveryRoute.length - 1;
        window.mapcenter["dmap"] = [deliveryRoute[rri][0], -deliveryRoute[rri][1]];
        $("#rp_speed").html(rrspeed);
        $("#rp_cur").html(rri + 1);
        $("#rp_pct").html(Math.round(rri / deliveryRoute.length * 100));
        dmapw = $("#dmap").width();
        dmaph = $("#dmap").height();
        if (prew != dmapw || preh != dmaph) {
            prew = dmapw;
            preh = dmaph;
            $(".dmap-player").remove();
            RenderPoint("dmap", 0, dmaph / 2, dmapw / 2, 5, nodetail = true, truckicon = true);
        }
        if (rri + 1 < deliveryRoute.length) {
            vx = Math.round((deliveryRoute[rri + 1][0] - deliveryRoute[rri][0]) * 100) / 100;
            vy = Math.round((deliveryRoute[rri + 1][1] - deliveryRoute[rri][1]) * 100) / 100;
            degree = Math.atan(vy / vx) / Math.PI * 180;
            if (!(vx == 0 && vy == 0)) {
                $(".dmap-player").css("rotate", parseInt(degree) + "deg");
                pred = degree;
                if (deliveryRoute[rri + 1][0] - deliveryRoute[rri][0] < 0) {
                    $(".dmap-player").css("transform", "scaleX(-1)");
                    pret = 1;
                } else {
                    $(".dmap-player").css("transform", "");
                    pret = 0;
                }
            } else {
                $(".dmap-player").css("rotate", parseInt(pred) + "deg");
                if (pret) {
                    $(".dmap-player").css("transform", "scaleX(-1)");
                } else {
                    $(".dmap-player").css("transform", "");
                }
            }
        } else {
            $(".dmap-player").css("rotate", parseInt(pred) + "deg");
            if (pret) {
                $(".dmap-player").css("transform", "scaleX(-1)");
            } else {
                $(".dmap-player").css("transform", "");
            }
        }

        x = deliveryRoute[rri][0];
        z = deliveryRoute[rri][1];
        lastevent = 0;
        for (var i = lastevent; i < rrevents.length; i++) {
            ex = rrevents[i].location.x;
            ez = rrevents[i].location.z;
            // distance of (x,z) and (ex,ez) <= 50, use euclid distance
            if (Math.sqrt(Math.pow(x - ex, 2) + Math.pow(z - ez, 2)) <= 50) {
                lastevent = i + 1;
                mt = $("#dmap").position().top;
                ml = $("#dmap").position().left;
                eventmsg = "";
                if (rrevents[i].type == "tollgate") {
                    cost = rrevents[i].meta.cost;
                    eventmsg = "Paid " + punit + TSeparator(cost) + " at toll gate.";
                } else if (rrevents[i].type == "refuel") {
                    amount = rrevents[i].meta.amount;
                    eventmsg = "Refueled " + TSeparator(parseInt(amount)) + "L of fuel.";
                } else if (rrevents[i].type == "collision") {
                    eventmsg = "Collision!";
                } else if (rrevents[i].type == "repair") {
                    eventmsg = "Truck repaired.";
                } else if (rrevents[i].type == "teleport") {
                    eventmsg = "Teleported.";
                } else if (rrevents[i].type == "fine") {
                    meta = rrevents[i].meta;
                    console.log(rrevents[i]);
                    finetype = meta.offence;
                    if (finetype == "speeding_camera") {
                        curspeed = TSeparator(parseInt(meta.speed * 3.6 / 1.6));
                        speedlimit = TSeparator(parseInt(meta.speed_limit * 3.6 / 1.6));
                        eventmsg = `Captured by speeding camera<br>${curspeed}Mi/h (Speed Limit ${speedlimit}Mi/h)<br>Fined ` + punit + TSeparator(meta.amount);
                    } else if (finetype == "speeding") {
                        curspeed = TSeparator(parseInt(meta.speed * 3.6 / 1.6));
                        speedlimit = TSeparator(parseInt(meta.speed_limit * 3.6 / 1.6));
                        eventmsg = `Caught by police car for speeding<br>${curspeed}Mi/h (Speed Limit ${speedlimit}Mi/h)<br>Fined ` + punit + TSeparator(meta.amount);
                    } else if (finetype == "crash") {
                        eventmsg = `Crash<br>Fined ` + punit + TSeparator(meta.amount);
                    } else if (finetype == "red_signal") {
                        eventmsg = `Red Signal Offence<br>Fined ` + punit + TSeparator(meta.amount);
                    }
                } else if (rrevents[i].type == "speeding") {
                    meta = rrevents[i].meta;
                    curspeed = TSeparator(parseInt(parseInt(meta.max_speed) * 3.6 / 1.6));
                    speedlimit = TSeparator(parseInt(parseInt(meta.speed_limit) * 3.6 / 1.6));
                    eventmsg = `Speeding (No Fine)<br>${curspeed}Mi/h (Speed Limit ${speedlimit}Mi/h)`;
                }
                if (eventmsg != "") {
                    randomid = Math.random().toString(36).substring(7);
                    $(".rrevent").hide();
                    $("#dmap").append(`<a class="rrevent" id="rrevent-${randomid}" style='position:absolute;top:${mt+dmaph/2}px;left:${ml+dmapw/2}px;color:red;'>${eventmsg}</a>`);
                    setTimeout(function () {
                        $("#rrevent-" + randomid).fadeOut();
                    }, 3000);
                }
            }
        }

        await sleep(500 / rrspeed);

        while (dmapint != -999) {
            await sleep(500);
            rri -= 1;
        }
    }
    $("#rrplay").html("Replay");
    setTimeout(function () {
        $(".dmap-player").remove();
        window.mapcenter["dmap"] = undefined;
    }, 5000);
}

function rrplayswitch() {
    if ($("#rrplay").html() == "Replay") deliveryDetail(curlogid);
    if (window.dn == undefined || window.dn.previousExtent_ == undefined) return toastFactory("error", "Error:", "Please zoom & drag the map to activate it.", 5000, false);
    if (dmapint == -999) {
        dmapint = -2;
        $("#rrplay").html("Play");
    } else {
        $("#rrplay").html("Pause");
        deliveryRoutePlay(50);
    }
}

function deliveryDetail(logid) {
    curlogid = logid;
    window.autofocus["dmap"] = -2;
    $("#routereplaydiv").hide();
    $("#routereplayload").show();
    rri = 0;
    rrspeed = 20;
    $("#DeliveryInfoBtn" + logid).attr("disabled", "disabled");
    $("#DeliveryInfoBtn" + logid).html("Loading...");
    $("#rp_cur").html("0");
    $("#rp_tot").html("0");
    $("#rp_pct").html("0");
    $("#rrplay").html("Play");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/dlog/detail?logid=" + String(logid),
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#DeliveryInfoBtn" + logid).removeAttr("disabled");
            $("#DeliveryInfoBtn" + logid).html("Show Details");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000,
                false);
            info = "";
            if (!data.error) {
                window.history.pushState("", "", '/delivery?logid=' + logid);
                d = data.response;
                userid = d.userid;
                name = d.name;
                d = d.data;
                tp = d.type;
                d = d.data.object;
                start_time = +new Date(d.start_time);
                stop_time = +new Date(d.stop_time);
                duration = "N/A";
                if (start_time > 86400 * 1000) duration = String((stop_time - start_time) / 1000).toHHMMSS(); // in case start time is 19700101 and timezone
                planned_distance = TSeparator(parseInt(d.planned_distance / 1.6)) + "Mi";
                fuel_used_org = d.fuel_used;
                fuel_used = TSeparator(parseInt(d.fuel_used)) + "L";
                cargo = d.cargo.name;
                cargo_mass = TSeparator(parseInt(d.cargo.mass)) + "kg";
                source_company = "Unknown company";
                source_city = "Unknown city";
                destination_company = "Unknown company";
                destination_city = "Unknown city";
                if (d.source_company != null) source_company = d.source_company.name;
                if (d.source_city != null) source_city = d.source_city.name;
                if (d.destination_company != null) destination_company = d.destination_company.name;
                if (d.destination_city != null) destination_city = d.destination_city.name;
                truck = d.truck.brand.name + " " + d.truck.name;
                license_plate = d.truck.license_plate_country.unique_id.toUpperCase() + " " + d.truck.license_plate;
                top_speed = parseInt(d.truck.top_speed * 3.6 / 1.6);
                trailer = "";
                trs = "";
                if (d.trailers.length > 1) trs = "s";
                for (var i = 0; i < d.trailers.length; i++) {
                    trailer += d.trailers[i].license_plate_country.unique_id.toUpperCase() + " " + d.trailers[i]
                        .license_plate + " | ";
                }
                punit = "€";
                if (!d.game.short_name.startsWith("e")) punit = "$";
                rrevents = d.events;
                meta = d.events[d.events.length - 1].meta;
                if (tp == "job.delivered") {
                    revenue = TSeparator(meta.revenue);
                    earned_xp = meta.earned_xp;
                    cargo_damage = meta.cargo_damage;
                    distance = TSeparator(parseInt(meta.distance / 1.6)) + "Mi";
                    auto_park = meta.auto_park;
                    auto_load = meta.auto_load;
                    avg_fuel = TSeparator(parseInt(fuel_used_org / (meta.distance / 1.6) * 100));
                } else if (tp == "job.cancelled") {
                    distance = TSeparator(parseInt(d.driven_distance / 1.6)) + "Mi";
                    distance_org = d.driven_distance;
                    penalty = TSeparator(meta.penalty);
                    avg_fuel = TSeparator(parseInt(fuel_used_org / (distance_org / 1.6) * 100));
                }

                $(".ddcol").children().remove();
                $("#ddcol1").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">From</td>
                        <td class="py-5 px-6 font-medium">${source_city}</td></tr>`);
                $("#ddcol1").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">To</td>
                        <td class="py-5 px-6 font-medium">${destination_city}</td></tr>`);
                $("#ddcol1").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Cargo</td>
                        <td class="py-5 px-6 font-medium">${cargo}</td></tr>`);
                $("#ddcol1").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Weight</td>
                        <td class="py-5 px-6 font-medium">${cargo_mass}</td></tr>`);
                $("#ddcol1").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Initial Company</td>
                        <td class="py-5 px-6 font-medium">${source_company}</td></tr>`);
                $("#ddcol1").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Target Company</td>
                        <td class="py-5 px-6 font-medium">${destination_company}</td></tr>`);
                $("#ddcol2").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Driven / Planned Distance</td>
                        <td class="py-5 px-6 font-medium">${distance} / ${planned_distance}</td></tr>`);
                offence = 0;
                for (var i = 0; i < rrevents.length; i++) {
                    if (rrevents[i].type == "fine") {
                        offence += parseInt(rrevents[i].meta.amount);
                    }
                }
                offence = TSeparator(offence);
                if (tp == "job.delivered") {
                    $("#ddcol2").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Profit</td>
                        <td class="py-5 px-6 font-medium">${revenue} ${punit}</td></tr>`);
                    $("#ddcol2").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Offence</td>
                        <td class="py-5 px-6 font-medium">-${offence} ${punit}</td></tr>`);
                    $("#ddcol2").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">XP</td>
                        <td class="py-5 px-6 font-medium">${earned_xp}</td></tr>`);
                    $("#ddcol2").append(`<tr class="text-xs">
                            <td class="py-5 px-6 font-medium">Damage</td>
                            <td class="py-5 px-6 font-medium">${parseInt(cargo_damage * 100)}%</td></tr>`);
                } else if (tp == "job.cancelled") {
                    $("#ddcol2").append(`<tr class="text-xs">
                            <td class="py-5 px-6 font-medium">Penalty</td>
                            <td class="py-5 px-6 font-medium">${penalty} ${punit}</td></tr>`);
                    $("#ddcol2").append(`<tr class="text-xs">
                            <td class="py-5 px-6 font-medium">Offence</td>
                            <td class="py-5 px-6 font-medium">-${offence} ${punit}</td></tr>`);
                    $("#ddcol2").append(`<tr class="text-xs">
                            <td class="py-5 px-6 font-medium">XP</td>
                            <td class="py-5 px-6 font-medium">0</td></tr>`);
                    $("#ddcol2").append(`<tr class="text-xs">
                            <td class="py-5 px-6 font-medium">Damage</td>
                            <td class="py-5 px-6 font-medium">${parseInt(data.response.data.data.object.cargo.damage * 100)}%</td></tr>`);
                }
                $("#ddcol2").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Maximal Reached Speed</td>
                        <td class="py-5 px-6 font-medium">${top_speed} Mi/h</td></tr>`);
                $("#ddcol3").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Truck</td>
                        <td class="py-5 px-6 font-medium">${truck}</td></tr>`);
                $("#ddcol3").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Truck's License Plate</td>
                        <td class="py-5 px-6 font-medium">${license_plate}</td></tr>`);
                $("#ddcol3").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Trailer's License Plate${trs}</td>
                        <td class="py-5 px-6 font-medium">${trailer.slice(0,-3)}</td></tr>`);
                $("#ddcol3").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Average Consumption</td>
                        <td class="py-5 px-6 font-medium">${avg_fuel}L/100Mi</td></tr>`);
                $("#ddcol3").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Fuel Used</td>
                        <td class="py-5 px-6 font-medium">${fuel_used}</td></tr>`);
                if (tp == "job.delivered") {
                    extra = "";
                    if (auto_park == "1") extra += "Auto Park | ";
                    if (auto_load == "1") extra += "Auto Load | ";
                    if (extra != "") {
                        $("#ddcol3").append(`<tr class="text-xs">
                            <td class="py-5 px-6 font-medium">Tags</td>
                            <td class="py-5 px-6 font-medium">${extra.slice(0, -3)}</td></tr>`);
                    }
                }

                dt = getDateTime(data.response.timestamp * 1000);

                $("#ddcol4").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Driver</td>
                        <td class="py-5 px-6 font-medium"><a style='cursor:pointer' onclick='loadProfile(${userid})'>${name}</a></td></tr>`);
                if (tp == "job.cancelled") {
                    $("#ddcol4").append(`<tr class="text-xs">
                            <td class="py-5 px-6 font-medium">Log ID</td>
                            <td class="py-5 px-6 font-medium">${logid} (Cancelled)</td></tr>`);
                } else {
                    $("#ddcol4").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Log ID</td>
                        <td class="py-5 px-6 font-medium">${logid}</td></tr>`);
                }
                $("#ddcol4").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Logged Distance</td>
                        <td class="py-5 px-6 font-medium">${parseInt(data.response.loggeddistance/1.6)}Mi</td></tr>`);
                $("#ddcol4").append(`<tr class="text-xs">
                        <td class="py-5 px-6 font-medium">Time submitted</td>
                        <td class="py-5 px-6 font-medium">${dt}</td></tr>`);

                $("#routereplayload").html("Route replay loading...");

                tabname = "#DeliveryDetailTab";
                $(".tabs").hide();
                $(tabname).show();
                setTimeout(function () {
                    telemetry = data.response.telemetry.split(";");
                    basic = telemetry[0].split(",");
                    tver = 1;
                    if (basic[0].startsWith("v2")) tver = 2;
                    if (basic[0].startsWith("v3")) tver = 3;
                    if (basic[0].startsWith("v4")) tver = 4;
                    basic[0] = basic[0].slice(2);
                    game = basic[0];
                    mods = basic[1];
                    route = telemetry.slice(1);
                    dpoints = [];
                    lastx = 0;
                    lastz = 0;
                    for (i = 0; i < route.length; i++) {
                        if (tver == 4) {
                            if (route[i].split(",") == 1 && route[i].startsWith("idle")) {
                                idlecnt = parseInt(route[i].split("e")[1]);
                                for (var j = 0; j < idlecnt; j++) {
                                    dpoints.push([lastx, lastz]);
                                }
                                continue;
                            }
                        }
                        p = route[i].split(",");
                        if (p.length < 2) continue;
                        if (tver == 1) dpoints.push([p[0], p[2]]); // x, z
                        else if (tver == 2) dpoints.push([b62decode(p[0]), b62decode(p[1])]);
                        else if (tver >= 3) {
                            relx = b62decode(p[0]);
                            relz = b62decode(p[1]);
                            dpoints.push([lastx + relx, lastz + relz]);
                            lastx = lastx + relx;
                            lastz = lastz + relz;
                        }
                    }
                    minx = 100000000000000;
                    for (i = 0; i < dpoints.length; i++) {
                        if (dpoints[i][0] < minx) minx = dpoints[i][0];
                    }
                    $("#dmap").children().remove();
                    window.dn = {};
                    window.mapcenter["dmap"] = undefined;
                    if (game == 1 && (mods == "promod" || JSON.stringify(data.response).toLowerCase().indexOf("promod") != -1)) {
                        LoadETS2PMap("dmap");
                    } else if (game == 1) { // ets2
                        LoadETS2Map("dmap");
                    } else if (game == 2) { // ats
                        LoadATSMap("dmap");
                    } else {
                        $("#routereplayload").html("Route replay not available.");
                        return;
                    }
                    setTimeout(function () {
                        $("#routereplayload").hide();
                        $("#routereplaydiv").fadeIn();
                    }, 2000);
                    deliveryRoute = dpoints;
                    $("#rp_tot").html(deliveryRoute.length);
                    dpoints150 = dpoints.filter(function (el, i) {
                        return i % 300 == 0;
                    });
                    dpoints30 = dpoints.filter(function (el, i) {
                        return i % 100 == 0;
                    });
                    dpoints20 = dpoints.filter(function (el, i) {
                        return i % 50 == 0;
                    });
                    dpoints10 = dpoints.filter(function (el, i) {
                        return i % 10 == 0;
                    });
                    dpoints = dpoints.filter(function (el, i) {
                        return i % 5 == 0;
                    });
                    window.dn = {};
                    if (dmapint != -1) clearInterval(dmapint);
                    dmapint = setInterval(function () {
                        if (window.dn == undefined || window.dn.previousExtent_ == undefined) return;
                        window.dmapRange = {};
                        dmapRange["top"] = window.dn.previousExtent_[3];
                        dmapRange["left"] = window.dn.previousExtent_[0];
                        dmapRange["bottom"] = window.dn.previousExtent_[1];
                        dmapRange["right"] = window.dn.previousExtent_[2];
                        $(".dmap-player").remove();
                        dmapxl = dmapRange["left"];
                        dmapxr = dmapRange["right"];
                        dmapyt = dmapRange["top"];
                        dmapyb = dmapRange["bottom"];
                        dmapw = $("#dmap").width();
                        dmaph = $("#dmap").height();
                        dscale = (dmapxr - dmapxl) / $("#dmap").width();
                        ddpoints = dpoints;
                        if (dscale >= 150 && i % 300 != 0) ddpoints = dpoints150;
                        else if (dscale >= 30 && i % 100 != 0) ddpoints = dpoints30;
                        else if (dscale >= 20 && i % 50 != 0) ddpoints = dpoints20;
                        else if (dscale >= 10 && i % 10 != 0) ddpoints = dpoints10;
                        for (var i = 0; i < ddpoints.length; i++) {
                            x = ddpoints[i][0];
                            z = -ddpoints[i][1];
                            if (x > dmapxl && x < dmapxr && z > dmapyb && z < dmapyt) {
                                rx = (x - dmapxl) / (dmapxr - dmapxl) * dmapw;
                                rz = (z - dmapyt) / (dmapyb - dmapyt) * dmaph;
                                RenderPoint("dmap", 0, rz, rx, 5, nodetail = true);
                            }
                        }
                    }, 500);
                }, 500);
            }
        },
        error: function (data) {
            ShowTab("#HomeTab", "#HomeTabBtn");
            $("#DeliveryInfoBtn" + logid).removeAttr("disabled");
            $("#DeliveryInfoBtn" + logid).html("Show Details");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to load delivery log details. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`
            );
            console.log(data);
        }
    });
}

allevents = {};

function loadEvent(recurse = true) {
    page = parseInt($("#epages").val())
    if (page == "") page = 1;
    if (page == undefined) page = 1;

    if (eventsCalendar == undefined) {
        $.ajax({
            url: "https://drivershub.charlws.com/atm/event/full",
            type: "GET",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + localStorage.getItem("token")
            },
            success: async function (data) {
                if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
                const d = data.response.list;
                var eventlist = [];
                offset = (+new Date().getTimezoneOffset()) * 60 * 1000;
                for (var i = 0; i < d.length; i++) {
                    eventlist.push({
                        "title": d[i].title,
                        "url": "/event?eventid=" + d[i].eventid,
                        "start": new Date(d[i].mts * 1000 - offset).toISOString().substring(0, 10)
                    })
                }

                setTimeout(async function () {
                    while ($("#loading").width() != 0) await sleep(50);
                    var eventsCalendarEl = document.getElementById('eventsCalendar');
                    var eventsCalendar = new FullCalendar.Calendar(eventsCalendarEl, {
                        initialView: 'dayGridMonth',
                        headerToolbar: {
                            left: 'prev,next today',
                            center: 'title'
                        },
                        eventClick: function (info) {
                            info.jsEvent.preventDefault();
                            eventid = parseInt(info.event.url.split("=")[1]);
                            eventDetail(eventid);
                        },
                        events: eventlist,
                        height: 'auto'
                    });
                    eventsCalendar.render();
                    setInterval(function () {
                        $(".fc-daygrid-event").removeClass("fc-daygrid-event");
                    }, 500);
                }, 50);
            },
            error: function (data) {
                toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
                console.warn(
                    `Failed to load events. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
                console.log(data);
            }
        })
    }

    $.ajax({
        url: "https://drivershub.charlws.com/atm/event?page=" + page,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            $("#eventTable").empty();
            const events = data.response.list;
            if (events.length == 0) {
                $("#eventTableHead").hide();
                $("#eventTable").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                $("#epages").val(1);
                if (recurse) loadEvent(recurse = false);
                return;
            }
            $("#eventTableHead").show();
            totpage = Math.ceil(data.response.tot / 10);
            if (page > totpage) {
                $("#epages").val(1);
                if (recurse) loadEvent(recurse = false);
                return;
            }
            if (page <= 0) {
                $("#epages").val(1);
                page = 1;
            }
            $("#etotpages").html(totpage);
            $("#eventTableControl").children().remove();
            $("#eventTableControl").append(`
            <button type="button" style="display:inline"
            class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
            onclick="$('#epages').val(1);loadEvent();">1</button>`);
            if (page > 3) {
                $("#eventTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            for (var i = Math.max(page - 1, 2); i <= Math.min(page + 1, totpage - 1); i++) {
                $("#eventTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#epages').val(${i});loadEvent();">${i}</button>`);
            }
            if (page < totpage - 2) {
                $("#eventTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            if (totpage > 1) {
                $("#eventTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#epages').val(${totpage});loadEvent();">${totpage}</button>`);
            }

            for (i = 0; i < events.length; i++) {
                const event = events[i];
                allevents[event.eventid] = event;
                mts = event.mts * 1000;
                dts = event.dts * 1000;
                now = +new Date();
                color = "";
                if (now >= mts - 1000 * 60 * 60 * 6) {
                    color = "blue";
                }
                if (now >= mts && now <= dts + 1000 * 60 * 30) {
                    color = "lightgreen"
                }
                if (now > dts + 1000 * 60 * 30) {
                    color = "grey";
                }
                mt = getDateTime(mts);
                dt = getDateTime(dts);
                voteids = event.voteid.split(",");
                voteids = voteids.filter(function (el) {
                    return el != "";
                });
                votecnt = voteids.length;
                pvt = "";
                if (event.private) pvt = "<span style='color:red'>(Private)</span> ";
                $("#eventTable").append(`
            <tr class="text-xs" style="color:${color}">
              <td class="py-5 px-6 font-medium">${event.eventid}</td>
              <td class="py-5 px-6 font-medium">${pvt} ${event.title}</td>
              <td class="py-5 px-6 font-medium">${event.departure}</td>
              <td class="py-5 px-6 font-medium">${event.destination}</td>
              <td class="py-5 px-6 font-medium">${event.distance}</td>
              <td class="py-5 px-6 font-medium">${mt}</td>
              <td class="py-5 px-6 font-medium">${dt}</td>
              <td class="py-5 px-6 font-medium">${votecnt}</td>
              <td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:grey" id="EventInfoBtn${event.eventid}" onclick="eventDetail('${event.eventid}')">Show Details</td>
            </tr>`);
            }
        },
        error: function (data) {
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(
                `Failed to load events. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function eventvote(eventid) {
    $.ajax({
        url: "https://drivershub.charlws.com/atm/event/vote",
        type: "POST",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        data: {
            "eventid": eventid
        },
        success: function (data) {
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            $("#eventid").val(eventid);
            FetchEvent(eventid, showdetail = eventid);
            return toastFactory("success", "Success:", data.response, 5000, false);
        },
        error: function (data) {
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to vote / unvote for event. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    });
}

async function eventDetail(eventid) {
    keys = Object.keys(allevents);
    if (keys.indexOf(String(eventid)) == -1) {
        $("#eventid").val(eventid);
        GeneralLoad();
        FetchEvent();
        while ($.active > 0) {
            await sleep(50);
        }
        keys = Object.keys(allevents);
        if (keys.indexOf(String(eventid)) == -1) {
            return toastFactory("error", "Error:", "Event not found.", 5000, false);
        }
    }
    event = allevents[eventid];
    voteop = `<a style="cursor:pointer;color:grey" onclick="eventvote(${eventid})">(Vote)</a>`;
    console.log(event);
    voteids = event.voteid.split(",");
    voteids = voteids.filter(function (el) {
        return el != "";
    });
    userid = localStorage.getItem("userid");
    if (voteids.indexOf(String(userid)) != -1) {
        voteop = `<a style="cursor:pointer;color:grey" onclick="eventvote(${eventid})">(Unvote)</a>`;
    }
    votecnt = voteids.length;
    info = `<div style="text-align:left">`;
    info += "<p><b>Event ID</b>: " + event.eventid + "</p>";
    info += "<p><b>From</b>: " + event.departure + "</p>";
    info += "<p><b>To</b>: " + event.destination + "</p>";
    info += "<p><b>Distance</b>: " + event.distance + "</p>";
    info += "<p><b>Meetup Time</b>: " + getDateTime(event.mts * 1000) + "</p>";
    info += "<p><b>Departure Time</b>: " + getDateTime(event.dts * 1000) + "</p>";
    info += "<p><b>Voted (" + votecnt + ")</b>: " + voteop + " " + event.vote + "</p>";
    info += "<p><b>Attendees</b>: " + event.attendee + "</p>";
    for (var i = 0; i < event.img.length; i++) {
        info += "<img src='" + event.img[i] + "' style='width:100%'/>";
    }
    info += "</div>";
    Swal.fire({
        title: `<a href='${event.tmplink}' target='_blank'>${event.title}</a>`,
        html: info,
        icon: 'info',
        confirmButtonText: 'Close'
    });
}

function loadMembers(recurse = true) {
    page = parseInt($("#mpages").val())
    if (page == "") page = 1;
    if (page == undefined) page = 1;
    GeneralLoad();
    $("#searchMemberBtn").html("...");
    $("#searchMemberBtn").attr("disabled", "disabled");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/member/list?page=" + page + "&search=" + $("#searchname").val(),
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#searchMemberBtn").html("Go");
            $("#searchMemberBtn").removeAttr("disabled");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            $("#membersTable").empty();
            const users = data.response.list;

            if (users.length == 0) {
                $("#membersTableHead").hide();
                $("#membersTable").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                $("#mpages").val(1);
                if (recurse) loadMembers(recurse = false);
                return;
            }
            $("#membersTableHead").show();
            totpage = Math.ceil(data.response.tot / 10);
            if (page > totpage) {
                $("#mpages").val(1);
                if (recurse) loadMembers(recurse = false);
                return;
            }
            if (page <= 0) {
                $("#mpages").val(1);
                page = 1;
            }
            $("#mtotpages").html(totpage);
            $("#membersTableControl").children().remove();
            $("#membersTableControl").append(`
            <button type="button" style="display:inline"
            class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
            onclick="$('#mpages').val(1);loadMembers();">1</button>`);
            if (page > 3) {
                $("#membersTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            for (var i = Math.max(page - 1, 2); i <= Math.min(page + 1, totpage - 1); i++) {
                $("#membersTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#mpages').val(${i});loadMembers();">${i}</button>`);
            }
            if (page < totpage - 2) {
                $("#membersTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            if (totpage > 1) {
                $("#membersTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#mpages').val(${totpage});loadMembers();">${totpage}</button>`);
            }

            for (i = 0; i < users.length; i++) {
                const user = users[i];
                // Fill the table using this format: 
                // <tr class="text-xs">
                //  <td class="py-5 px-6 font-medium">id here</td>
                //    <td class="py-5 px-6 font-medium">name here</td>
                //  </tr>
                //
                highestrole = user.highestrole;
                color = "blue"; // Member
                if (highestrole < 100) color = "#ff0000"; // Staff
                if (highestrole <= 9) color = "#770202"; // Leadership
                if (highestrole > 100 || highestrole == 99) color = "grey"; // External / LOA
                highestrole = rolelist[highestrole];
                if (highestrole == undefined) highestrole = "/";
                discordid = user.discordid;
                avatar = user.avatar;
                totalpnt = parseInt(user.totalpnt);
                src = "";
                if (avatar != null) {
                    if (avatar.startsWith("a_"))
                        src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif";
                    else
                        src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png";
                } else {
                    avatar = "/images/atm-black.png";
                }
                $("#membersTable").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium">${user.userid}</td>
              <td class="py-5 px-6 font-medium" style="color:${color}">
                <a style="cursor:pointer;" onclick="loadProfile('${user.userid}')">
                <img src='${src}' width="20px" style="display:inline;border-radius:100%"> ${user.name}</a></td>
              <td class="py-5 px-6 font-medium" style="color:${color}">${highestrole}</td>
            </tr>`);
            }

            user = data.response.staff_of_the_month;
            discordid = user.discordid;
            avatar = user.avatar;
            src = "";
            if (avatar != null) {
                if (avatar.startsWith("a_"))
                    src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif";
                else
                    src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png";
            } else {
                avatar = "/images/atm-black.png";
            }
            $("#sotm").html(`<a style='cursor:pointer' onclick='loadProfile("${user.userid}")'>${user.name}</a>`);
            $("#sotma").attr("src", src);

            user = data.response.driver_of_the_month;
            discordid = user.discordid;
            avatar = user.avatar;
            src = "";
            if (avatar != null) {
                if (avatar.startsWith("a_"))
                    src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif";
                else
                    src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png";
            }
            $("#dotm").html(`<a style='cursor:pointer' onclick='loadProfile("${user.userid}")'>${user.name}</a>`);
            $("#dotma").attr("src", src);

        },
        error: function (data) {
            $("#searchMemberBtn").html("Go");
            $("#searchMemberBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(`Failed to load members. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function loadAuditLog(recurse = true) {
    page = parseInt($("#auditpages").val())
    if (page == "") page = 1;
    if (page == undefined) page = 1;
    $.ajax({
        url: "https://drivershub.charlws.com/atm/auditlog?page=" + page,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            $("#auditTable").empty();
            const audits = data.response.list;

            if (audits.length == 0) {
                $("#auditTableHead").hide();
                $("#auditTable").append(`
        <tr class="text-xs">
          <td class="py-5 px-6 font-medium">No Data</td>
          <td class="py-5 px-6 font-medium"></td>
          <td class="py-5 px-6 font-medium"></td>
        </tr>`);
                $("#auditpages").val(1);
                if (recurse) loadAuditLog(recurse = false);
                return;
            }
            $("#auditTableHead").show();
            totpage = Math.ceil(data.response.tot / 30);
            if (page > totpage) {
                $("#auditpages").val(1);
                if (recurse) loadAuditLog(recurse = false);
                return;
            }
            if (page <= 0) {
                $("#auditpages").val(1);
                page = 1;
            }
            $("#audittotpages").html(totpage);
            $("#auditTableControl").children().remove();
            $("#auditTableControl").append(`
            <button type="button" style="display:inline"
            class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
            onclick="$('#auditpages').val(1);loadAuditLog();">1</button>`);
            if (page > 3) {
                $("#auditTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            for (var i = Math.max(page - 1, 2); i <= Math.min(page + 1, totpage - 1); i++) {
                $("#auditTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#auditpages').val(${i});loadAuditLog();">${i}</button>`);
            }
            if (page < totpage - 2) {
                $("#auditTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            if (totpage > 1) {
                $("#auditTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#auditpages').val(${totpage});loadAuditLog();">${totpage}</button>`);
            }

            for (i = 0; i < audits.length; i++) {
                audit = audits[i];
                dt = getDateTime(audit.timestamp * 1000);
                op = parseMarkdown(audit.operation).replace("\n", "<br>");
                $("#auditTable").append(`
        <tr class="text-xs">
          <td class="py-5 px-6 font-medium">${audit.user}</td>
          <td class="py-5 px-6 font-medium">${op}</td>
          <td class="py-5 px-6 font-medium">${dt}</td>
        </tr>`);
            }
        },
        error: function (data) {
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(
                `Failed to load audit log. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function memberDetail(userid) {
    $("#MemberInfoBtn" + userid).attr("disabled", "disabled");
    $("#MemberInfoBtn" + userid).html("Loading...");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/member/info?userid=" + String(userid),
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000,
                false);
            info = "";
            if (!data.error) {
                d = data.response;
                roles = d.roles;
                rtxt = "";
                for (var i = 0; i < roles.length; i++)
                    if (rolelist[roles[i]] != undefined) rtxt += rolelist[roles[i]] + ", ";
                    else rtxt += "Unknown Role (ID " + roles[i] + "), ";
                rtxt = rtxt.substring(0, rtxt.length - 2);
                info += "<p style='text-align:left'><b>Name:</b> " + d.name + "</p>";
                info += "<p style='text-align:left'><b>User ID:</b> " + d.userid + "</p>"
                info += "<p style='text-align:left'><b>Roles:</b> " + rtxt + "</p>";
                if (d.email != undefined) info += "<p style='text-align:left'><b>Email:</b> " + d.email + "</p>";
                info += "<p style='text-align:left'><b>Discord ID:</b> " + d.discordid + "</p>";
                info +=
                    "<p style='text-align:left'><b>TruckersMP ID:</b> <a href='https://truckersmp.com/user/" +
                    d.truckersmpid + "'>" + d.truckersmpid + "</a></p>";
                info +=
                    "<p style='text-align:left'><b>Steam ID:</b> <a href='https://steamcommunity.com/profiles/" +
                    d.steamid + "'>" + d.steamid + "</a></p>";
                info += "<br><p style='text-align:left'><b>Join:</b> " + getDateTime(d.join * 1000) + "</p>";
                info += "<p style='text-align:left'><b>Total Jobs:</b> " + d.totjobs + "</p>";
                info += "<p style='text-align:left'><b>Distance Driven:</b> " + parseInt(d.distance / 1.6) + "Mi</p>";
                info += "<p style='text-align:left'><b>Fuel Consumed:</b> " + parseInt(d.fuel) + "L</p>";
                info += "<p style='text-align:left'><b>XP Earned:</b> " + d.xp + "</p>";
                info += "<p style='text-align:left'><b>Event Points:</b> " + parseInt(d.eventpnt) + "</p>";
                info += "<p style='text-align:left'><b>Total Points:</b> " + parseInt(d.distance / 1.6 + d.eventpnt) +
                    "</p>";

            }
            Swal.fire({
                title: d.name,
                html: info,
                icon: 'info',
                confirmButtonText: 'Close'
            })
            $("#MemberInfoBtn" + userid).removeAttr("disabled");
            $("#MemberInfoBtn" + userid).html("Show Details");
        },
        error: function (data) {
            $("#MemberInfoBtn" + userid).removeAttr("disabled");
            $("#MemberInfoBtn" + userid).html("Show Details");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to load member details. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    });
}

lastfetch = -1;

function fetchRoles() {
    val = $("#memberroleid").val();
    GeneralLoad();
    $("#fetchRolesBtn").html("Working...");
    $("#fetchRolesBtn").attr("disabled", "disabled");
    $("#rolelist").children().children().prop("checked", false);
    $("#memberrolename").html("");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/member/list?page=1&search=" + val,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#fetchRolesBtn").html("Fetch Existing Roles");
            $("#fetchRolesBtn").removeAttr("disabled");
            d = data.response.list;
            if (d.length == 0) {
                return toastFactory("error", "Error:", "No member with name " + val + " found.", 5000, false);
            }
            lastfetch = d[0].userid;

            $.ajax({
                url: "https://drivershub.charlws.com/atm/member/info?userid=" + String(lastfetch),
                type: "GET",
                dataType: "json",
                headers: {
                    "Authorization": "Bearer " + localStorage.getItem("token")
                },
                success: function (data) {
                    $("#fetchRolesBtn").html("Fetch Existing Roles");
                    $("#fetchRolesBtn").removeAttr("disabled");
                    if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
                    info = "";
                    if (!data.error) {
                        userid = lastfetch;
                        d = data.response;
                        roles = d.roles;
                        rtxt = "";
                        $("#memberrolename").html(d.name + " (" + userid + ")");
                        for (var i = 0; i < roles.length; i++)
                            $("#role" + roles[i]).prop("checked", true);
                        return toastFactory("success", "Success!", "Existing roles are fetched!", 5000, false);
                    }
                },
                error: function (data) {
                    $("#fetchRolesBtn").html("Fetch Existing Roles");
                    $("#fetchRolesBtn").removeAttr("disabled");
                    toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                        false);
                    console.warn(
                        `Failed to load member details. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
                    console.log(data);
                }
            });
        },
        error: function (data) {
            return toastFactory("error", "Error:", "Failed to get User ID", 5000, false);
        }
    })
}

function updateMemberRoles() {
    userid = lastfetch;
    GeneralLoad();
    $("#updateMemberRolesBtn").html("Working...");
    $("#updateMemberRolesBtn").attr("disabled", "disabled");
    d = $('input[name="assignrole"]:checked');
    roles = [];
    for (var i = 0; i < d.length; i++) {
        roles.push(d[i].id.replaceAll("role", ""));
    }
    $.ajax({
        url: "https://drivershub.charlws.com/atm/member/role",
        type: "POST",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        data: {
            "userid": userid,
            "roles": roles.join(",")
        },
        success: function (data) {
            $("#updateMemberRolesBtn").html("Update");
            $("#updateMemberRolesBtn").removeAttr("disabled");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            info = "";
            if (!data.error) {
                return toastFactory("success", "Success!", "Member roles updated!", 5000, false);
            }
        },
        error: function (data) {
            $("#updateMemberRolesBtn").html("Update");
            $("#updateMemberRolesBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to load member details. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    });
}

function updateMemberPoints() {
    userid = $("#memberpntid").val();
    if (!isNumber(userid)) {
        toastFactory("error", "Error:", "Please enter a valid user ID.", 5000, false);
        return;
    }
    miles = $("#memberpntmile").val();
    eventpnt = $("#memberpntevent").val();
    if (!isNumber(miles)) {
        miles = 0;
    }
    if (!isNumber(eventpnt)) {
        eventpnt = 0;
    }
    GeneralLoad();
    $("#updateMemberPointsBtn").html("Working...");
    $("#updateMemberPointsBtn").attr("disabled", "disabled");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/member/point",
        type: "POST",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        data: {
            "userid": userid,
            "mile": miles,
            "eventpnt": eventpnt
        },
        success: function (data) {
            $("#updateMemberPointsBtn").html("Update");
            $("#updateMemberPointsBtn").removeAttr("disabled");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            info = "";
            if (!data.error) {
                return toastFactory("success", "Success!", "Member points updated!", 5000, false);
            }
        },
        error: function (data) {
            $("#updateMemberPointsBtn").html("Update");
            $("#updateMemberPointsBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to load member details. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    });
}

dismissid = 0;

function dismissUser() {
    userid = $("#dismissUserID").val();
    if ($("#dismissbtn").html() != "Confirm?" || dismissid != userid) {
        $("#dismissbtn").html("Fetching name...");
        $("#dismissbtn").attr("disabled", "disabled");
        $.ajax({
            url: "https://drivershub.charlws.com/atm/member/info?userid=" + String(userid),
            type: "GET",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + localStorage.getItem("token")
            },
            success: function (data) {
                $("#dismissbtn").html("Dismiss");
                $("#dismissbtn").removeAttr("disabled");
                $("#memberdismissname").html("");
                if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
                info = "";
                if (!data.error) {
                    lastfetch = userid;
                    d = data.response;
                    roles = d.roles;
                    rtxt = "";
                    $("#memberdismissname").html("Dismiss <b>" + d.name + "</b>?");
                    $("#dismissbtn").html("Confirm?");
                    dismissid = userid;
                }
            },
            error: function (data) {
                $("#dismissbtn").html("Dismiss");
                $("#dismissbtn").removeAttr("disabled");
                toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                    false);
                console.warn(
                    `Failed to load member details. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
                console.log(data);
            }
        });
        return;
    }
    GeneralLoad();
    $("#dismissbtn").html("Working...");
    $("#dismissbtn").attr("disabled", "disabled");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/member/dismiss?userid=" + String(userid),
        type: "DELETE",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#memberdismissname").html("");
            $("#dismissUserID").val("");
            $("#dismissbtn").removeAttr("disabled");
            $("#dismissbtn").html("Dismiss");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000,
                false);
            return toastFactory("success", "Success", "Member dismissed", 5000, false);
        },
        error: function (data) {
            $("#dismissbtn").removeAttr("disabled");
            $("#dismissbtn").html("Dismiss");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to dismiss member. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    });
}

curprofile = -1;

function loadUserDelivery(recurse = true) {
    page = parseInt($("#udpages").val())
    if (page == "") page = 1;
    if (page == undefined) page = 1;
    GeneralLoad();
    $("#loadUserDeliveryBtn").html("...");
    $("#loadUserDeliveryBtn").attr("disabled", "disabled");
    starttime = -1;
    endtime = -1;
    if ($("#udstart").val() != "" && $("#udend").val() != "") {
        starttime = +new Date($("#udstart").val()) / 1000;
        endtime = +new Date($("#udend").val()) / 1000;
    }
    speedlimit = parseInt($("#udspeedlimit").val());
    if (!isNumber(speedlimit)) {
        speedlimit = 0;
    } else {
        speedlimit *= 1.6;
    }
    console.log(speedlimit);
    $.ajax({
        url: "https://drivershub.charlws.com/atm/dlog/list?quserid=" + curprofile + "&speedlimit=" + parseInt(speedlimit) + "&page=" + page + "&starttime=" + starttime + "&endtime=" + endtime,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#loadUserDeliveryBtn").html("Go");
            $("#loadUserDeliveryBtn").removeAttr("disabled");
            if (data.userDeliveryTable) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            $("#userDeliveryTable").empty();
            const deliveries = data.response.list;

            if (deliveries.length == 0) {
                $("#userDeliveryTableHead").hide();
                $("#userDeliveryTable").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                $("#udpages").val(1);
                if (recurse) loadUserDelivery(recurse = false);
                return;
            }
            $("#userDeliveryTableHead").show();
            totpage = Math.ceil(data.response.tot / 10);
            if (page > totpage) {
                $("#udpages").val(1);
                if (recurse) loadUserDelivery(recurse = false);
                return;
            }
            if (page <= 0) {
                $("#udpages").val(1);
                page = 1;
            }
            $("#udtotpages").html(totpage);
            $("#userDeliveryTableControl").children().remove();
            $("#userDeliveryTableControl").append(`
            <button type="button" style="display:inline"
            class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
            onclick="$('#udpages').val(1);loadUserDelivery();">1</button>`);
            if (page > 3) {
                $("#userDeliveryTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            for (var i = Math.max(page - 1, 2); i <= Math.min(page + 1, totpage - 1); i++) {
                $("#userDeliveryTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#udpages').val(${i});loadUserDelivery();">${i}</button>`);
            }
            if (page < totpage - 2) {
                $("#userDeliveryTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            if (totpage > 1) {
                $("#userDeliveryTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#udpages').val(${totpage});loadUserDelivery();">${totpage}</button>`);
            }

            for (i = 0; i < deliveries.length; i++) {
                const delivery = deliveries[i];
                // Fill the table using this format: 
                // <tr class="text-xs">
                //  <td class="py-5 px-6 font-medium">id here</td>
                //    <td class="py-5 px-6 font-medium">name here</td>
                //  </tr>
                //
                distance = TSeparator(parseInt(delivery.distance / 1.6));
                cargo_mass = parseInt(delivery.cargo_mass / 1000);
                unittxt = "€";
                if (delivery.unit == 2) unittxt = "$";
                profit = TSeparator(delivery.profit);
                color = "";
                if (delivery.profit < 0) color = "grey";
                dtl = "";
                if (localStorage.getItem("token") != "guest") {
                    dtl =
                        `<td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:grey" id="DeliveryInfoBtn${delivery.logid}" onclick="deliveryDetail('${delivery.logid}')">Show Details</td>`;
                }
                $("#userDeliveryTable").append(`
            <tr class="text-xs" style="color:${color}">
              <td class="py-5 px-6 font-medium">${delivery.logid}</td>
              <td class="py-5 px-6 font-medium">${delivery.source_company}, ${delivery.source_city}</td>
              <td class="py-5 px-6 font-medium">${delivery.destination_company}, ${delivery.destination_city}</td>
              <td class="py-5 px-6 font-medium">${distance}Mi</td>
              <td class="py-5 px-6 font-medium">${delivery.cargo} (${cargo_mass}t)</td>
              <td class="py-5 px-6 font-medium">${unittxt}${profit}</td>
              ${dtl}
            </tr>`);
            }
        },
        error: function (data) {
            $("#loadUserDeliveryBtn").html("Go");
            $("#loadUserDeliveryBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(
                `Failed to load delivery log. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function loadProfile(userid) {
    if (userid < 0) {
        return;
    }
    $("#aucs1").attr("onclick", `chartscale=1;loadChart(${userid});`);
    $("#aucs2").attr("onclick", `chartscale=2;loadChart(${userid});`);
    $("#aucs3").attr("onclick", `chartscale=3;loadChart(${userid});`);
    $("#aaddup1").attr("onclick", `addup=1-addup;loadChart(${userid});`);
    loadChart(userid);
    $("#udpages").val("1");
    curprofile = userid;
    loadUserDelivery(userid);
    if (curtab != "#ProfileTab") {
        ShowTab("#ProfileTab", userid);
        return;
    }
    $.ajax({
        url: "https://drivershub.charlws.com/atm/member/info?userid=" + String(userid),
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: async function (data) {
            if (data.error) {
                ShowTab("#HomeTab", "#HomeTabBtn");
                return toastFactory("error", "Error:", data.descriptor, 5000, false);
            }
            info = "";
            if (!data.error) {
                window.history.pushState("", "", '/member?userid=' + userid);
                d = data.response;
                info += "<h1 style='font-size:40px'>" + d.name + "</h1>";
                info += "<p><b>User ID:</b> " + d.userid + "</p>"
                info += "<p><b>Roles:</b> <span id='profileRoles'></span></p>";
                if (d.email != undefined) info += "<p><b>Email:</b> " + d.email + "</p>";
                info += "<p><b>Discord ID:</b> " + d.discordid + "</p>";
                info +=
                    "<p><b>TruckersMP ID:</b> <a href='https://truckersmp.com/user/" +
                    d.truckersmpid + "'>" + d.truckersmpid + "</a></p>";
                info +=
                    "<p><b>Steam ID:</b> <a href='https://steamcommunity.com/profiles/" +
                    d.steamid + "'>" + d.steamid + "</a></p>";
                info += "<br><p><b>Join:</b> " + getDateTime(d.join * 1000) + "</p>";
                info += "<p><b>Total Jobs:</b> " + d.totjobs + "</p>";
                info += "<p><b>Distance Driven:</b> " + parseInt(d.distance / 1.6) + "Mi</p>";
                info += "<p><b>Fuel Consumed:</b> " + parseInt(d.fuel) + "L</p>";
                info += "<p><b>XP Earned:</b> " + d.xp + "</p>";
                info += "<p><b>Event Points:</b> " + parseInt(d.eventpnt) + "</p>";
                info += "<p><b>Total Points:</b> " + parseInt(d.distance / 1.6 + d.eventpnt) +
                    "</p>";
                info += "<br><b>About Me:</b><br>" + parseMarkdown(d.bio) + "<br><br>";

                avatar = d.avatar;
                if (avatar != null) {
                    if (avatar.startsWith("a_"))
                        src = "https://cdn.discordapp.com/avatars/" + d.discordid + "/" + avatar + ".gif";
                    else
                        src = "https://cdn.discordapp.com/avatars/" + d.discordid + "/" + avatar + ".png";
                    $("#UserProfileAvatar").attr("src", src);
                } else {
                    avatar = "/images/atm-black.png";
                }

                $("#userProfileDetail").html(info);
                roles = d.roles;
                rtxt = "";
                for (var i = 0; i < roles.length; i++) {
                    if (roles[i] == 0) color = "rgba(127,127,127,0.4)";
                    else if (roles[i] < 10) color = "#770202";
                    else if (roles[i] <= 98) color = "#ff0000";
                    else if (roles[i] == 99) color = "#4e6f7b";
                    else if (roles[i] == 100) color = "#b30000";
                    else if (roles[i] > 100) color = "grey";
                    if (roles[i] == 223 || roles[i] == 224) color = "#ffff77;color:black;";
                    if (roles[i] == 1000) color = "#9146ff";
                    if (rolelist[roles[i]] != undefined) rtxt += `<span class='tag' style='max-width:fit-content;display:inline;background-color:${color}'>` + rolelist[roles[i]] + "</span> ";
                    else rtxt += "Unknown Role (ID " + roles[i] + "), ";
                }
                rtxt = rtxt.substring(0, rtxt.length - 2);
                $("#profileRoles").html(rtxt);

                if (d.userid == localStorage.getItem("userid")) {
                    $("#UpdateAM").show();
                    $("#Security").show();
                    $("#biocontent").val(d.bio);
                } else {
                    $("#UpdateAM").hide();
                    $("#Security").hide();
                }
            }
        },
        error: function (data) {
            ShowTab("#HomeTab", "#HomeTabBtn");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to load member details. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    });
}

function updateBio() {
    bio = $("#biocontent").val();
    $("#updateBioBtn").html("Updating...");
    $("#updateBioBtn").attr("disabled", "disabled");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/user/bio",
        type: "POST",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        data: {
            "bio": bio
        },
        success: function (data) {
            $("#updateBioBtn").html("Update");
            $("#updateBioBtn").removeAttr("disabled");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            info = "";
            if (!data.error) {
                loadProfile(localStorage.getItem("userid"));
                return toastFactory("success", "Success!", "About Me updated!", 5000, false);
            }
        },
        error: function (data) {
            $("#updateBioBtn").html("Update");
            $("#updateBioBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to update About Me. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    });
}

function genNewAppToken() {
    GeneralLoad();
    $("#genAppTokenBtn").html("Working...");
    $("#genAppTokenBtn").attr("disabled", "disabled");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/user/apptoken",
        type: "POST",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#genAppTokenBtn").html("Reset Token");
            $("#genAppTokenBtn").removeAttr("disabled");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            $("#userAppToken").html(data.response.token);
            return toastFactory("success", "Success", "Application Token generated!", 5000, false);
        },
        error: function (data) {
            $("#genAppTokenBtn").html("Reset Token");
            $("#genAppTokenBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to generate app token. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    });
}

function resign() {
    if ($("#resignBtn").html() != "Confirm?") {
        $("#resignBtn").html("Confirm?");
        return;
    }
    GeneralLoad();
    $("#resignBtn").html("Working...");
    $("#resignBtn").attr("disabled", "disabled");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/member/resign",
        type: "DELETE",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            $("#resignBtn").html("Resign");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            info = "";
            if (!data.error) {
                localStorage.clear();
                Swal.fire({
                    title: "Resigned",
                    html: "Sorry to see you leave, good luck with your futuer career!",
                    icon: 'info',
                    confirmButtonText: 'Close'
                })
            }
        },
        error: function (data) {
            $("#resignBtn").html("Resign");
            $("#resignBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to resign. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    });
}

bannedUser = {};

function loadUsers(recurse = true) {
    page = parseInt($("#pupages").val())
    if (page == "") page = 1;
    if (page == undefined) page = 1;
    $.ajax({
        url: "https://drivershub.charlws.com/atm/user/list?page=" + page,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            $("#usersTable").empty();
            const users = data.response.list;

            if (users.length == 0) {
                $("#usersTableHead").hide();
                $("#usersTable").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                $("#pupages").val(1);
                if (recurse) loadUsers(recurse = false);
                return;
            }
            $("#usersTableHead").show();
            totpage = Math.ceil(data.response.tot / 10);
            if (page > totpage) {
                $("#pupages").val(1);
                if (recurse) loadUsers(recurse = false);
                return;
            }
            if (page <= 0) {
                $("#pupages").val(1);
                page = 1;
            }
            $("#putotpages").html(totpage);
            $("#usersTableControl").children().remove();
            $("#usersTableControl").append(`
            <button type="button" style="display:inline"
            class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
            onclick="$('#pupages').val(1);loadUsers();">1</button>`);
            if (page > 3) {
                $("#usersTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            for (var i = Math.max(page - 1, 2); i <= Math.min(page + 1, totpage - 1); i++) {
                $("#usersTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#pupages').val(${i});loadUsers();">${i}</button>`);
            }
            if (page < totpage - 2) {
                $("#usersTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            if (totpage > 1) {
                $("#usersTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#pupages').val(${totpage});loadUsers();">${totpage}</button>`);
            }

            for (i = 0; i < users.length; i++) {
                const user = users[i];
                // Fill the table using this format: 
                // <tr class="text-xs">
                //  <td class="py-5 px-6 font-medium">id here</td>
                //    <td class="py-5 px-6 font-medium">name here</td>
                //  </tr>
                //
                bantxt = "Ban";
                bantxt2 = "";
                color = "";
                accept = `<td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:grey">Accept as member</td>`;;
                if (user.banned) color = "grey", bantxt = "Unban", bantxt2 = "(Banned)", bannedUser[user.discordid] = user.banreason;
                else accept = `<td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:lightgreen" id="UserAddBtn${user.discordid}" onclick="addUser('${user.discordid}')">Accept as member</td>`;
                $("#usersTable").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium" style='color:${color}'>${user.discordid}</td>
              <td class="py-5 px-6 font-medium" style='color:${color}'>${user.name} ${bantxt2}</td>
              ${accept}
              <td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:red" onclick="banGo('${user.discordid}')">${bantxt}</td>
              <td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:grey" id="UserInfoBtn${user.discordid}" onclick="userDetail('${user.discordid}')">Show Details</td>
            </tr>`)
            }
        },
        error: function (data) {
            toastFactory("error", "Error:", "Please check the console for more info.", 5000, false);
            console.warn(`Failed to load users. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function banGo(discordid) {
    $("#bandiscordid").val(discordid);
    document.getElementById("BanUserDiv").scrollIntoView();
}

function addUser(discordid = -1) {
    if (discordid == -1) {
        discordid = $("#adddiscordid").val();
        if (!isNumber(discordid)) {
            return toastFactory("error", "Error:", "Please enter a valid discord id.", 5000, false);
        }
    } else {
        if ($("#UserAddBtn" + discordid).html() != "Confirm?") {
            $("#UserAddBtn" + discordid).html("Confirm?");
            $("#UserAddBtn" + discordid).css("color", "orange");
            return;
        }
    }
    $.ajax({
        url: "https://drivershub.charlws.com/atm/member/add",
        type: "POSt",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        data: {
            discordid: discordid
        },
        success: function (data) {
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000,
                false);
            toastFactory("success", "Success", "User added successfully. User ID: " + data.response.userid, 5000,
                false);
            loadUsers();
        },
        error: function (data) {
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to add user. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function userDetail(discordid) {
    $("#UserInfoBtn" + discordid).attr("disabled", "disabled");
    $("#UserInfoBtn" + discordid).html("Loading...");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/user/info?qdiscordid=" + String(discordid),
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000,
                false);
            info = "";
            if (!data.error) {
                d = data.response;
                info += "<p style='text-align:left'><b>Name:</b> " + d.name + "</p>";
                info += "<p style='text-align:left'><b>Email:</b> " + d.email + "</p>";
                info += "<p style='text-align:left'><b>Discord ID:</b> " + discordid + "</p>";
                info +=
                    "<p style='text-align:left'><b>TruckersMP ID:</b> <a href='https://truckersmp.com/user/" +
                    d.truckersmpid + "'>" + d.truckersmpid + "</a></p>";
                info +=
                    "<p style='text-align:left'><b>Steam ID:</b> <a href='https://steamcommunity.com/profiles/" +
                    d.steamid + "'>" + d.steamid + "</a></p><br>";
                if (Object.keys(bannedUser).indexOf(discordid) != -1) info += "<p style='text-align:left'><b>Ban Reason:</b> " + bannedUser[discordid] + "</p>";
            }
            bantxt = "";
            if (Object.keys(bannedUser).indexOf(discordid) != -1) bantxt = " (Banned)";
            if (bantxt == "") {
                Swal.fire({
                    title: d.name + bantxt,
                    html: info,
                    icon: 'info',
                    confirmButtonText: 'Close'
                })
            } else {
                Swal.fire({
                    title: d.name + bantxt,
                    html: info,
                    icon: 'error',
                    confirmButtonText: 'Close'
                })
            }
            $("#UserInfoBtn" + discordid).removeAttr("disabled");
            $("#UserInfoBtn" + discordid).html("Show Details");
        },
        error: function (data) {
            $("#UserInfoBtn" + discordid).attr("disabled", "disabled");
            $("#UserInfoBtn" + discordid).html("Loading...");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to load user details. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    });
}

function banUser() {
    discordid = $("#bandiscordid").val();
    if (!isNumber(discordid)) {
        return toastFactory("error", "Error:", "Please enter a valid discord id.", 5000, false);
    }
    expire = -1;
    if ($("#banexpire").val() != "") {
        expire = +new Date($("#banexpire").val()) / 1000;
    }
    reason = $("#banreason").val();
    $.ajax({
        url: "https://drivershub.charlws.com/atm/user/ban",
        type: "POSt",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        data: {
            discordid: discordid,
            expire: expire,
            reason: reason
        },
        success: function (data) {
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000,
                false);
            loadUsers();
            toastFactory("success", "Success", "User banned successfully.", 5000, false);
        },
        error: function (data) {
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to ban user. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function unbanUser() {
    discordid = $("#bandiscordid").val();
    if (!isNumber(discordid)) {
        return toastFactory("error", "Error:", "Please enter a valid discord id.", 5000, false);
    }
    $.ajax({
        url: "https://drivershub.charlws.com/atm/user/unban",
        type: "POSt",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        data: {
            discordid: discordid
        },
        success: function (data) {
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000,
                false);
            toastFactory("success", "Success", "User unbanned successfully.", 5000, false);
        },
        error: function (data) {
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to unban user. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function loadMyApp(recurse = true) {
    page = parseInt($("#myapppage").val())
    $.ajax({
        url: "https://drivershub.charlws.com/atm/application/list?page=" + page + "&apptype=0",
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000,
                false);
            $("#myappTable").empty();
            const applications = data.response.list;
            APPTYPE = ["", "Driver", "Staff", "LOA"];
            STATUS = ["Pending", "Accepted", "Declined"]
            if (applications.length == 0) {
                $("#myappTableHead").hide();
                $("#myappTable").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                $("#myapppage").val(1);
                if (recurse) loadMyApp(recurse = false);
                return;
            }
            $("#myappTableHead").show();
            totpage = Math.ceil(data.response.tot / 10);
            if (page > totpage) {
                $("#myapppage").val(1);
                if (recurse) loadMyApp(recurse = false);
                return;
            }
            if (page <= 0) {
                $("#myapppage").val(1);
                page = 1;
            }
            $("#myapptotpages").html(totpage);
            $("#myAppTableControl").children().remove();
            $("#myAppTableControl").append(`
            <button type="button" style="display:inline"
            class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
            onclick="$('#myapppage').val(1);loadMyApp();">1</button>`);
            if (page > 3) {
                $("#myAppTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            for (var i = Math.max(page - 1, 2); i <= Math.min(page + 1, totpage - 1); i++) {
                $("#myAppTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#myapppage').val(${i});loadMyApp();">${i}</button>`);
            }
            if (page < totpage - 2) {
                $("#myAppTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            if (totpage > 1) {
                $("#myAppTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#myapppage').val(${totpage});loadMyApp();">${totpage}</button>`);
            }

            for (i = 0; i < applications.length; i++) {
                const application = applications[i];
                // Fill the table using this format: 
                // <tr class="text-xs">
                //  <td class="py-5 px-6 font-medium">id here</td>
                //    <td class="py-5 px-6 font-medium">name here</td>
                //  </tr>
                //
                apptype = APPTYPE[application.apptype];
                creation = getDateTime(application.submitTimestamp * 1000);
                closedat = getDateTime(application.closedTimestamp * 1000);
                if (application.closedTimestamp == 0) {
                    closedat = "/";
                    console.log(closedat);
                }
                status = STATUS[application.status];

                color = "blue";
                if (application.status == 1) color = "lightgreen";
                if (application.status == 2) color = "red";

                $("#myappTable").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium">${application.applicationid}</td>
              <td class="py-5 px-6 font-medium">${apptype}</td>
              <td class="py-5 px-6 font-medium">${creation}</td>
              <td class="py-5 px-6 font-medium" style="color:${color}">${status}</td>
              <td class="py-5 px-6 font-medium">${closedat}</td>
              <td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:grey" id="MyAppBtn${application.applicationid}" onclick="appDetail(${application.applicationid})">Show Details</td>
            </tr>`);
            }
        },
        error: function (data) {
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to load applications. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function addAppMessage() {
    appid = $("#appmsgid").val();
    if (!isNumber(appid)) {
        toastFactory("error", "Error:", "Please enter a valid application ID.", 5000, false);
        return;
    }
    message = $("#appmsgcontent").val();
    $("#addAppMessageBtn").html("Adding...");
    $("#addAppMessageBtn").attr("disabled", "disabled");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/application",
        type: "PATCH",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        data: {
            "applicationid": appid,
            "message": message
        },
        success: function (data) {
            $("#addAppMessageBtn").html("Add");
            $("#addAppMessageBtn").removeAttr("disabled");
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000, false);
            info = "";
            if (!data.error) {
                return toastFactory("success", "Success!", "Message added!", 5000, false);
            }
        },
        error: function (data) {
            $("#addAppMessageBtn").html("Add");
            $("#addAppMessageBtn").removeAttr("disabled");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to load member details. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    });
}

function loadAllApp(recurse = true) {
    page = parseInt($('#allapppage').val())
    $.ajax({
        url: "https://drivershub.charlws.com/atm/application/list?page=" + page + "&apptype=0&showall=1",
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            console.log(data);
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000,
                false);
            $("#allappTable").empty();
            $("#totpages").html(Math.ceil(data.response.tot / 10));
            $("#allapppage").val(data.response.page);
            const applications = data.response.list;
            APPTYPE = ["", "Driver", "Staff", "LOA"];
            STATUS = ["Pending", "Accepted", "Declined"];
            if (applications.length == 0) {
                $("#allappTableHead").hide();
                $("#allappTable").append(`
            <tr class="text-xs">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                $("#allapppage").val(1);
                if (recurse) loadAllApp(recurse = false);
                return;
            }
            $("#allappTableHead").show();
            totpage = Math.ceil(data.response.tot / 10);
            if (page > totpage) {
                $("#allapppage").val(1);
                if (recurse) loadAllApp(recurse = false);
                return;
            }
            if (page <= 0) {
                $("#allapppage").val(1);
                page = 1;
            }
            $("#allapptotpages").html(totpage);
            $("#allAppTableControl").children().remove();
            $("#allAppTableControl").append(`
            <button type="button" style="display:inline"
            class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
            onclick="$('#allapppage').val(1);loadAllApp();">1</button>`);
            if (page > 3) {
                $("#allAppTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            for (var i = Math.max(page - 1, 2); i <= Math.min(page + 1, totpage - 1); i++) {
                $("#allAppTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#allapppage').val(${i});loadAllApp();">${i}</button>`);
            }
            if (page < totpage - 2) {
                $("#allAppTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                >...</button>`);
            }
            if (totpage > 1) {
                $("#allAppTableControl").append(`
                <button type="button" style="display:inline"
                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                onclick="$('#allapppage').val(${totpage});loadAllApp();">${totpage}</button>`);
            }

            for (i = 0; i < applications.length; i++) {
                const application = applications[i];
                // Fill the table using this format: 
                // <tr class="text-xs">
                //  <td class="py-5 px-6 font-medium">id here</td>
                //    <td class="py-5 px-6 font-medium">name here</td>
                //  </tr>
                //
                apptype = APPTYPE[application.apptype];
                creation = getDateTime(application.submitTimestamp * 1000);
                closedat = getDateTime(application.closedTimestamp * 1000);
                if (application.closedTimestamp == 0) {
                    closedat = "/";
                    console.log(closedat);
                }
                status = STATUS[application.status];

                color = "blue";
                if (application.status == 1) color = "lightgreen";
                if (application.status == 2) color = "red";

                $("#allappTable").append(`
            <tr class="text-xs" id="AllApp${application.applicationid}">
              <td class="py-5 px-6 font-medium">${application.applicationid}</td>
              <td class="py-5 px-6 font-medium">${application.name}</td>
              <td class="py-5 px-6 font-medium">${apptype}</td>
              <td class="py-5 px-6 font-medium">${creation}</td>
              <td class="py-5 px-6 font-medium" style="color:${color}">${status}</td>
              <td class="py-5 px-6 font-medium">${closedat}</td>
              <td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:grey" id="AllAppBtn${application.applicationid}" onclick="appDetail(${application.applicationid}, true)">Show Details</td>
            </tr>`);
            }
        },
        error: function (data) {
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to load applications. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function appDetail(applicationid, staffmode = false) {
    $("#AllAppBtn" + applicationid).attr("disabled", "disabled");
    $("#AllAppBtn" + applicationid).html("Loading...");
    $("#MyAppBtn" + applicationid).attr("disabled", "disabled");
    $("#MyAppBtn" + applicationid).html("Loading...");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/application?applicationid=" + applicationid,
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        success: function (data) {
            if (data.error) return toastFactory("error", "Error:", data.descriptor, 5000,
                false);
            d = data.response.data;
            discordid = data.response.discordid;
            keys = Object.keys(d);
            if (keys.length == 0) {
                return toastFactory("error", "Error:", "Application has no data", 5000,
                    false);
            }
            APPTYPE = ["", "Driver", "Staff", "LOA"];
            apptype = APPTYPE[data.response.apptype];
            ret = "";
            for (i = 0; i < keys.length; i++) {
                ret += "<p style='text-align:left'><b>" + keys[i] + ":</b><br> " + d[keys[i]] + "</p><br>";
            }
            ret += "";

            $.ajax({
                url: "https://drivershub.charlws.com/atm/user/info?qdiscordid=" + String(discordid),
                type: "GET",
                dataType: "json",
                headers: {
                    "Authorization": "Bearer " + localStorage.getItem("token")
                },
                success: function (data) {
                    info = "";
                    if (!data.error) {
                        d = data.response;
                        info += "<p style='text-align:left'><b>Name:</b> " + d.name + "</p>";
                        info += "<p style='text-align:left'><b>Email:</b> " + d.email + "</p>";
                        info += "<p style='text-align:left'><b>Discord ID:</b> " + discordid + "</p>";
                        info +=
                            "<p style='text-align:left'><b>TruckersMP ID:</b> <a href='https://truckersmp.com/user/" +
                            d.truckersmpid + "'>" + d.truckersmpid + "</a></p>";
                        info +=
                            "<p style='text-align:left'><b>Steam ID:</b> <a href='https://steamcommunity.com/profiles/" +
                            d.steamid + "'>" + d.steamid + "</a></p><br>";
                        info += ret.replaceAll("\n", "<br>");
                        if (!staffmode) {
                            info += `
                            <hr>
                            <h3 class="text-xl font-bold" style="text-align:left;margin:5px">New message</h3>
                            <div class="mb-6" style="display:none">
                                <label class="block text-sm font-medium mb-2" for="">Application ID</label>
                                <input id="appmsgid" style="width:200px"
                                class="block w-full px-4 py-3 mb-2 text-sm placeholder-gray-500 bg-white border rounded" name="field-name"
                                rows="5" placeholder="Integar ID" value="${applicationid}"></input>
                            </div>
                                <textarea id="appmsgcontent"
                                class="block w-full px-4 py-3 mb-2 text-sm placeholder-gray-500 bg-white border rounded" name="field-name"
                                rows="5" placeholder=""></textarea>
                    
                            <button type="button" id="addAppMessageBtn" style="float:right"
                                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                                onclick="addAppMessage()">Add</button>`;
                        } else {
                            info += `
                            <hr>
                            <h3 class="text-xl font-bold" style="text-align:left;margin:5px">New message</h3>
                            <div class="mb-6" style="display:none">
                                <label class="block text-sm font-medium mb-2" for="">Application ID</label>
                                <input id="appstatusid" style="width:200px"
                                class="block w-full px-4 py-3 mb-2 text-sm placeholder-gray-500 bg-white border rounded" name="field-name"
                                rows="5" placeholder="" value="${applicationid}"></input></div>
                    
                            <div class="mb-6">
                                <textarea id="appmessage"
                                class="block w-full px-4 py-3 mb-2 text-sm placeholder-gray-500 bg-white border rounded" name="field-name"
                                rows="5" placeholder=""></textarea></div>
                    
                            <div class="mb-6 relative" style="width:200px">
                            <h3 class="text-xl font-bold" style="text-align:left;margin:5px">New Status</h3>
                                <select id="appstatussel"
                                class="appearance-none block w-full px-4 py-3 mb-2 text-sm placeholder-gray-500 bg-white border rounded"
                                name="field-name">
                                <option value="0">Pending</option>
                                <option value="1">Accepted</option>
                                <option value="2">Declined</option>
                                </select>
                                <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
                                <svg class="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewbox="0 0 20 20">
                                    <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"></path>
                                </svg>
                                </div>
                            </div>
                    
                            <button type="button" style="float:right"
                                class="w-full md:w-auto px-6 py-3 font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded transition duration-200"
                                onclick="updateAppStatus()" id="updateAppStatusBtn">Update</button>
                            </div>
                        </div>`;
                        }
                    }
                    Swal.fire({
                        title: apptype + ' Application #' + applicationid,
                        html: info,
                        icon: 'info',
                        showConfirmButton: false,
                        confirmButtonText: 'Close'
                    })
                    $("#AllAppBtn" + applicationid).removeAttr("disabled");
                    $("#AllAppBtn" + applicationid).html("Show Details");
                    $("#MyAppBtn" + applicationid).removeAttr("disabled");
                    $("#MyAppBtn" + applicationid).html("Show Details");
                }
            });
        },
        error: function (data) {
            $("#AllAppBtn" + applicationid).removeAttr("disabled");
            $("#AllAppBtn" + applicationid).html("Show Details");
            $("#MyAppBtn" + applicationid).removeAttr("disabled");
            $("#MyAppBtn" + applicationid).html("Show Details");
            toastFactory("error", "Error:", "Please check the console for more info.", 5000,
                false);
            console.warn(
                `Failed to load applications. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function updateAppStatus() {
    $("#updateAppStatusBtn").attr("disabled", true);
    $("#updateAppStatusBtn").html("Updating...");
    appid = $("#appstatusid").val();
    appstatus = parseInt($("#appstatussel").find(":selected").val());
    message = $("#appmessage").val();
    $.ajax({
        url: "https://drivershub.charlws.com/atm/application/status",
        type: "POST",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        data: {
            "applicationid": appid,
            "status": appstatus,
            "message": message
        },
        success: function (data) {
            $("#updateAppStatusBtn").removeAttr("disabled");
            $("#updateAppStatusBtn").html("Update");
            if (data.error) return toastFactory("error", "Error:", data.descriptor,
                5000, false);
            else {
                loadAllApp();
                return toastFactory("success", "Application status updated.", data.response.message, 5000, false);
            }
        },
        error: function (data) {
            $("#updateAppStatusBtn").removeAttr("disabled");
            $("#updateAppStat usBtn").html("Update");
            toastFactory("error", "Error:", "Please check the console for more info.",
                5000,
                false);
            console.warn(
                `Failed to load applications. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function updateStaffPosition() {
    $("#updateStaffPositionBtn").attr("disabled", true);
    $("#updateStaffPositionBtn").html("Updating...");
    positions = $("#staffposedit").val().replaceAll("\n", ",");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/application/positions",
        type: "POST",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + localStorage.getItem("token")
        },
        data: {
            "positions": positions
        },
        success: function (data) {
            $("#updateStaffPositionBtn").removeAttr("disabled");
            $("#updateStaffPositionBtn").html("Update");
            if (data.error) return toastFactory("error", "Error:", data.descriptor,
                5000, false);
            else {
                return toastFactory("success", "Success!", data.response.message, 5000, false);
            }
        },
        error: function (data) {
            $("#updateStaffPositionBtn").removeAttr("disabled");
            $("#updateStaffPositionBtn").html("Update");
            toastFactory("error", "Error:", "Please check the console for more info.",
                5000,
                false);
            console.warn(
                `Failed to load applications. Error: ${data.descriptor ? data.descriptor : 'Unknown Error'}`);
            console.log(data);
        }
    })
}

function PathDetect() {
    p = window.location.pathname;
    console.log(p);
    if (p == "/") ShowTab("#HomeTab", "#HomeTabBtn");
    else if (p == "/announcement") ShowTab("#AnnTab", "#AnnTabBtn");
    else if (p == "/staffannouncement") ShowTab("#StaffAnnTab", "#StaffAnnTabBtn");
    else if (p == "/map") ShowTab("#Map", "#MapBtn");
    else if (p == "/delivery") {
        logid = getUrlParameter("logid");
        if (logid) {
            $(".tabbtns").removeClass("bg-indigo-500");
            $("#DeliveryBtn").addClass("bg-indigo-500");
            deliveryDetail(logid);
        } else ShowTab("#Delivery", "#DeliveryBtn");
    } else if (p == "/event") ShowTab("#Event", "#EventBtn");
    else if (p == "/staffevent") ShowTab("#StaffEvent", "#StaffEventBtn");
    else if (p == "/member") {
        userid = getUrlParameter("userid");
        if (userid) loadProfile(parseInt(userid));
        else ShowTab("#AllMembers", "#AllMemberBtn");
    } else if (p == "/staffmember") {
        ShowTab("#StaffMembers", "#StaffMemberBtn");
    } else if (p == "/leaderboard") ShowTab("#Leaderboard", "#LeaderboardBtn");
    else if (p == "/ranking") ShowTab("#Ranking", "#RankingBtn");
    else if (p == "/myapp") ShowTab("#MyApp", "#MyAppBtn");
    else if (p == "/allapp") ShowTab("#AllApp", "#AllAppBtn");
    else if (p == "/submitapp") ShowTab("#SubmitApp", "#SubmitAppBtn");
    else if (p == "/pendinguser") ShowTab("#AllUsers", "#AllUserBtn");
    else if (p == "/audit") ShowTab("#AuditLog", "#AuditLogBtn");
    else ShowTab("#HomeTab", "#HomeTabBtn");
}

window.onpopstate = function (event) {
    PathDetect();
};

$(document).ready(function () {
    if (localStorage.getItem("darkmode") == "1") {
        $("body").addClass("bg-gray-800");
        $("body").css("color", "white");
        $("head").append(`<style id='convertbg'>
            h1,h2,h3,p,span,text,label,input,textarea,select,tr {color: white;}
            .text-gray-500,.text-gray-600 {color: #ddd;}
            .bg-white {background-color: rgba(255, 255, 255, 0.2);}
            .swal2-popup {background-color: rgb(41 48 57)}
            .rounded-full {background-color: #888}
            th > .fc-scrollgrid-sync-inner {background-color: #444}</style>`);
        $("#todarksvg").hide();
        $("#tolightsvg").show();
        Chart.defaults.color = "white";
        $("body").html($("body").html().replaceAll("text-green", "text-temp"));
        $("body").html($("body").html().replaceAll("#382CDD", "skyblue").replaceAll("green", "lightgreen"));
        $("body").html($("body").html().replaceAll("text-temp", "text-green"));
    } else {
        $("head").append(`<style>
            .rounded-full {background-color: #ddd}</style>`);
    }
    var date = new Date();
    var firstDay = new Date(date.getFullYear(), date.getMonth(), 1);
    offset = (+new Date().getTimezoneOffset()) * 60 * 1000;
    firstDay = new Date(+firstDay - offset);
    date = new Date(+date - offset);
    $("#lbstart").val(firstDay.toISOString().substring(0, 10));
    $("#lbend").val(date.toISOString().substring(0, 10));
    validate();
    PathDetect();

    if (navigator.userAgent.match(/Android/i) || navigator.userAgent.match(/webOS/i) || navigator.userAgent.match(/iPhone/i) || navigator.userAgent.match(/iPad/i) || navigator.userAgent.match(/iPod/i) || navigator.userAgent.match(/BlackBerry/i) || navigator.userAgent.match(/Windows Phone/i)) {
        t = $("div");
        for (i = 0; i < t.length; i++) {
            st = $(t[i]).attr("style");
            if (st == undefined) continue;
            st = st.replaceAll("padding:50px", "padding:5px");
            $(t[i]).attr("style", st);
        }
        $("#hometableftcontainer").css("width", "100%");
    }

    $('#searchname').keydown(function (e) {
        if (e.which == 13) loadMembers();
    });
    $('#dend,#dspeedlimit').keydown(function (e) {
        if (e.which == 13) loadDelivery();
    });
    $('#udend,#udspeedlimit').keydown(function (e) {
        if (e.which == 13) loadUserDelivery();
    });
    $('#lbend,#lbspeedlimit').keydown(function (e) {
        if (e.which == 13) loadLeaderboard();
    });
    $('#memberroleid').keydown(function (e) {
        if (e.which == 13) fetchRoles();
    });
    $('#attendeeId').keydown(function (e) {
        var keyCode = e.keyCode || e.which;
        if (keyCode == 13) {
            val = $("#attendeeId").val();
            if (val == "") return;
            $.ajax({
                url: "https://drivershub.charlws.com/atm/member/list?page=1&search=" + val,
                type: "GET",
                dataType: "json",
                headers: {
                    "Authorization": "Bearer " + localStorage.getItem("token")
                },
                success: function (data) {
                    d = data.response.list;
                    if (d.length == 0) {
                        return toastFactory("error", "Error:", "No member with name " + val + " found.", 5000, false);
                    }
                    userid = d[0].userid;
                    username = d[0].name;
                    if ($(`#attendeeid-${userid}`).length > 0) {
                        return toastFactory("error", "Error:", "Member already added.", 5000, false);
                    }
                    $("#attendeeId").before(`<span class='tag attendee' id='attendeeid-${userid}'>${username} (${userid})
                        <a style='cursor:pointer' onclick='$("#attendeeid-${userid}").remove()'><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x" viewBox="0 0 16 16"> <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/> </svg> </a></span>`);
                    $("#attendeeId").val("");
                },
                error: function (data) {
                    return toastFactory("error", "Error:", "Failed to get User ID", 5000, false);
                }
            })
        } else if (keyCode == 8) {
            e.preventDefault();
            val = $("#attendeeId").val();
            if (val != "") {
                $("#attendeeId").val(val.substring(0, val.length - 1));
                return;
            }
            ch = $("#attendeeIdWrap").children();
            ch[ch.length - 2].remove();
        }
    });

    function devwarn() {
        for (var i = 0; i < 3; i++) {
            setTimeout(function () {
                console.log("%cHold Up!", "color: #0000ff; font-size: 100px;");
                console.log(
                    "%cYou are likely to be hacked if anyone ask you to paste something here, or look for data in Local Storage!",
                    "color:red; font-size: 15px;");
                console.log(
                    "%cUnless you understand exactly what you are doing, close this window and stay safe.",
                    "font-size: 15px;");
                console.log(
                    "%cIf you do understand exactly what you are doing, you should come work with us, simply submit an application and we'll get back to you very soon",
                    "font-size: 15px;");
            }, 800 * i);
        }
    }
    //devwarn();
    $("body").keydown(function (e) {
        var keyCode = e.keyCode || e.which;
        if (keyCode == 123) {
            devwarn();
        }
    });

    setInterval(function () {
        if ($("#HomeTab").width() / 3 <= 300) {
            if ($("#HomeTab").width() / 2 <= 300) {
                $(".statscard").css("width", "100%");
            } else {
                $(".statscard").css("width", "50%");
            }
        } else {
            $(".statscard").css("width", "33%");
        }
    }, 10);

    $("#pupages").val("1");
    $("#allapppage").val("1");
    $("#myapppage").val("1");

    $("#logout").click(function () {
        token = localStorage.getItem("token")
        $.ajax({
            url: "https://drivershub.charlws.com/atm/user/revoke",
            type: "POST",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + token
            },
            success: function (data) {
                localStorage.removeItem("token");
                window.location.href = "/login";
            },
            error: function (data) {
                localStorage.removeItem("token");
                window.location.href = "/login";
            }
        });
    });
    $('#appselect').on('change', function () {
        var value = $(this).val();
        $(".apptabs").hide();
        if (value == "driver") {
            $("#DriverApp").show();
        } else if (value == "staff") {
            $("#StaffApp").show();
        } else if (value == "loa") {
            $("#LOAApp").show();
        }
    });
    annpage = 2;
    $.ajax({
        url: "https://drivershub.charlws.com/atm/announcement?page=1",
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + token
        },
        success: function (data) {
            ann = data.response.list;
            if (ann.length > 0) {
                a = ann[0];
                dt = getDateTime(a.timestamp * 1000);
                content = "<span style='font-size:10px;color:grey'><b>#" + a.aid + "</b> | <b>" + dt +
                    "</b> by <a style='cursor:pointer' onclick='loadProfile(" + a.byuserid + ")'><i>" + a.by + "</i></a></span><br>" + a
                    .content.replaceAll("\n", "<br>");
                TYPES = ["info", "info", "warning", "criticle", "resolved"];
                banner = genBanner(TYPES[a.atype], a.title, content);
                $("#HomeTabLeft").append(banner.replaceAll("py-8 ", "pb-8 "));
            }
            for (i = 0; i < ann.length; i++) {
                a = ann[i];
                dt = getDateTime(a.timestamp * 1000);
                content = "<span style='font-size:10  px;color:grey'><b>#" + a.aid + "</b> | <b>" + dt +
                    "</b> by <a style='cursor:pointer' onclick='loadProfile(" + a.byuserid + ")'><i>" + a.by + "</i></a></span><br>" + a
                    .content.replaceAll("\n", "<br>");
                TYPES = ["info", "info", "warning", "criticle", "resolved"];
                banner = genBanner(TYPES[a.atype], a.title, content);
                $("#anns").append(banner);
            }
        }
    });
    lastPositionsUpdate = parseInt(localStorage.getItem("positionsLastUpdate"));
    if (!isNumber(lastPositionsUpdate)) {
        lastPositionsUpdate = 0;
    }
    if (+new Date() - lastPositionsUpdate > 86400) {
        $.ajax({
            url: "https://drivershub.charlws.com/atm/application/positions",
            type: "GET",
            dataType: "json",
            success: function (data) {
                positions = data.response;
                positionstxt = "";
                for (var i = 0; i < positions.length; i++) {
                    positionstxt += positions[i] + "\n";
                    $("#sa-select").append("<option>" + positions[i] + "</option>");
                }
                positionstxt = positionstxt.slice(0, -1);
                $("#staffposedit").val(positionstxt);
                localStorage.setItem("positionsLastUpdate", +new Date());
                localStorage.setItem("positions", JSON.stringify(positions));
            }
        });
    }
    window.onscroll = function (ev) {
        if (curtab != "#AnnTab") return;
        if ((window.innerHeight + window.scrollY + 100) >= document.body.offsetHeight) {
            $.ajax({
                url: "https://drivershub.charlws.com/atm/announcement?page=" + annpage,
                type: "GET",
                dataType: "json",
                headers: {
                    "Authorization": "Bearer " + token
                },
                success: async function (data) {
                    annpage += 1;
                    ann = data.response.list;
                    for (i = 0; i < ann.length; i++) {
                        a = ann[i];
                        dt = getDateTime(a.timestamp * 1000);
                        content = "<span style='font-size:10px;color:grey'><b>#" + a.aid + "</b> | <b>" + dt +
                            "</b> by <a style='cursor:pointer' onclick='loadProfile(" + a.byuserid + ")'><i>" + a.by + "</i></a></span><br>" +
                            a
                            .content.replaceAll("\n", "<br>");
                        TYPES = ["info", "info", "warning", "criticle", "resolved"];
                        banner = genBanner(TYPES[a.atype], a.title, content);
                        $("#anns").append(banner);
                        $($("#anns").children()[$("#anns").children().length - 1]).hide();
                        $($("#anns").children()[$("#anns").children().length - 1]).fadeIn();
                        await sleep(200);
                    }
                    if (ann.length == 0) {
                        toastFactory("info", "No more announcements", "You have reached the end of the list", 5000,
                            false);
                        $("#annloadmore").attr("disabled", "disabled");
                    }
                }
            });
        }
    };
});