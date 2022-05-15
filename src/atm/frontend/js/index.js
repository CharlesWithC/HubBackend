rolelist = {};

token = localStorage.getItem("token");
$(".pageinput").val("1");

function loadStats() {
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
            $("#allfuel").html(fuel);
            $("#newfuel").html(newfuel);
        }
    });
    $.ajax({
        url: "https://drivershub.charlws.com/atm/dlog/leaderboard",
        type: "GET",
        dataType: "json",
        headers: {
            "Authorization": "Bearer " + token
        },
        success: function (data) {
            users = data.response.list;
            $("#leaderboard").empty();
            for (var i = 0; i < 5; i++) {
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
                $("#leaderboard").append(`<tr class="text-xs bg-gray-50">
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
            users = data.response.list;
            $("#newdriverTable").empty();
            for (var i = 0; i < 5; i++) {
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
                $("#newdriverTable").append(`<tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">
                <a style="cursor: pointer" onclick="loadProfile(${userid})"><img src='${src}' width="20px" style="display:inline;border-radius:100%"> ${name}</a></td>
              <td class="py-5 px-6">${joindt}</td>
            </tr>`);
            }
        }
    });
}

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

function ShowTab(tabname, btnname) {
    $(".tabs").hide();
    $(tabname).show();
    $(".tabbtns").removeClass("bg-indigo-500");
    $(btnname).addClass("bg-indigo-500");
    if(tabname == "#Map"){
        LoadETS2Map();
        LoadATSMap();
    }
    if (tabname == "#SubmitApp") {
        $("#driverappsel").attr("selected", "selected");
    }
    if (tabname == "#MyApp") {
        loadMyApp();
    }
    if (tabname == "#AllApp") {
        loadAllApp();
    }
    if (tabname == "#AllUsers") {
        loadUsers();
    }
    if (tabname == "#AllMembers") {
        loadMembers();
    }
    if (tabname == "#Delivery") {
        loadDelivery();
    }
    if (tabname == "#Event") {
        loadEvent();
    }
    if (tabname == "#ProfileTab") {
        loadProfile(localStorage.getItem("userid"));
    }
    if (tabname == "#AuditLog") {
        loadAuditLog();
    }
    if (tabname == "#Leaderboard") {
        loadLeaderboard();
    }
}

function FetchAnnouncement() {
    aid = $("#annid").val();

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

function FetchEvent() {
    eventid = $("#eventid").val();
    if (!isNumber(eventid)) {
        return toastFactory("error", "Error", "Event ID must be in integar!", 5000, false);
    }

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
            $("#eventimgs").val(imgs);
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

        // Check if any of the fields are empty
        if (q1 == "" || q2 == "" || q3 == "") {
            toastFactory("warning", "Error", "You must fill in all the fields!", 5000, false);
            return;
        }

        data = {
            "Start Date": q1,
            "End Date": q2,
            "Reason": q3
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
    $("#newann").hide();
    if (roles != null && roles != undefined) {
        highestrole = 99999;
        for (i = 0; i < roles.length; i++) {
            if (roles[i] < highestrole) {
                highestrole = roles[i];
                if (roles[i] == 40 || roles[i] == 41) {
                    $("#newann").show(); // event staff
                    $("#newevent").show(); // event staff
                    $("#eventattendee").show();
                    if (roles[i] == 40) {
                        $("#annrole").html("Event Manager");
                    } else {
                        $("#annrole").html("Event Staff");
                    }
                    setInterval(function () {
                        title = $("#anntitle").val();
                        content = $("#anncontent").val();
                        annid = $("#annid").val();
                        if (isNumber(annid)) {
                            if (title != "" || content != "") {
                                $("#newAnnBtn").html("Update Announcement");
                                $("#newAnnBtn").css("background-color", "green");
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
                                $("#newEventBtn").css("background-color", "green");
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
        if (highestrole < 100) {
            $("#stafftabs").show();
            if (highestrole >= 30) {
                $("#AllAppBtn").hide();
                $("#AllMemberStaff").hide();
            } else {
                $("#AllMemberStaff").show();
                $("#AllAppBtn").show();
            }
        }
        if (highestrole <= 10) {
            $("#newann").show();
            $("#newevent").show(); // event staff
            $("#eventattendee").show();
            setInterval(function () {
                title = $("#anntitle").val();
                content = $("#anncontent").val();
                annid = $("#annid").val();
                if (isNumber(annid)) {
                    if (title != "" || content != "") {
                        $("#newAnnBtn").html("Update Announcement");
                        $("#newAnnBtn").css("background-color", "green");
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
                        $("#newEventBtn").css("background-color", "green");
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
    if (userid != -1) {
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
                    "<p style='color:orange'>Steam not bound! You must bind it to become a member! <a style='color:grey' href='/auth?token=" +
                    token + "'>Click here to bind it</a></p>");
            } else if (data.response.extra == "truckersmp") {
                $("#header").prepend(
                    "<p style='color:orange'>TruckersMP not bound! You must bind it to become a member! <a style='color:grey' href='/auth?token=" +
                    token + "'>Click here to bind it</a></p>");
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
                roles = data.response.roles;
                highestrole = 99999;
                for (i = 0; i < roles.length; i++) {
                    if (roles[i] < highestrole) {
                        highestrole = roles[i];
                    }
                }
                ShowStaffTabs();
                name = data.response.name;
                avatar = data.response.avatar;
                discordid = data.response.discordid;
                $("#name").html(name);
                if (avatar.startsWith("a_"))
                    $("#avatar").attr("src", "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif");
                else
                    $("#avatar").attr("src", "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png");
                $.ajax({
                    url: "https://drivershub.charlws.com/atm/member/roles",
                    type: "GET",
                    dataType: "json",
                    success: function (data) {
                        rolelist = data.response;
                        hrole = data.response[highestrole];
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
                });
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
            } else {
                localStorage.removeItem("token");
                window.location.href = "/login";
            }
        },
        error: function (data) {
            localStorage.removeItem("token");
            window.location.href = "/login";
        }
    });
}

function loadLeaderboard() {
    page = $("#lpages").val();
    if (page == "") page = 1;
    if (page == undefined) page = 1;
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
        url: "https://drivershub.charlws.com/atm/dlog/leaderboard?page=" + page + "&speedlimit=" + speedlimit + "&starttime=" + starttime + "&endtime=" + endtime,
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
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                return;
            }
            $("#leaderboardTableHead").show();
            $("#ltotpages").html(Math.ceil(data.response.tot / 10));
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
                $("#leaderboardTable").append(`<tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">
                <a style="cursor: pointer" onclick="loadProfile(${userid})"><img src='${src}' width="20px" style="display:inline;border-radius:100%"> ${name}</a></td>
                <td class="py-5 px-6">${point2rank(user.totalpnt)}</td>
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

function loadDelivery() {
    page = $("#dpages").val();
    if (page == "") page = 1;
    if (page == undefined) page = 1;
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
        url: "https://drivershub.charlws.com/atm/dlog/list?page=" + page + "&speedlimit=" + speedlimit + "&starttime=" + starttime + "&endtime=" + endtime,
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
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                return;
            }
            $("#deliveryTableHead").show();
            $("#dtotpages").html(Math.ceil(data.response.tot / 10));
            for (i = 0; i < deliveries.length; i++) {
                const delivery = deliveries[i];
                // Fill the table using this format: 
                // <tr class="text-xs bg-gray-50">
                //  <td class="py-5 px-6 font-medium">id here</td>
                //    <td class="py-5 px-6 font-medium">name here</td>
                //  </tr>
                //
                distance = TSeparator(parseInt(delivery.distance / 1.6));
                cargo_mass = parseInt(delivery.cargo_mass / 1000);
                unittxt = "€";
                if (delivery.unit == 2) unittxt = "$";
                profit = TSeparator(delivery.profit);
                color = "black";
                if (delivery.profit < 0) color = "grey";
                dtl = "";
                if (localStorage.getItem("token") != "guest") {
                    dtl =
                        `<td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:grey" id="DeliveryInfoBtn${delivery.logid}" onclick="deliveryDetail('${delivery.logid}')">Show Details</td>`;
                }
                $("#deliveryTable").append(`
            <tr class="text-xs bg-gray-50" style="color:${color}">
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

function deliveryDetail(logid) {
    $("#DeliveryInfoBtn" + logid).attr("disabled", "disabled");
    $("#DeliveryInfoBtn" + logid).html("Loading...");
    $.ajax({
        url: "https://drivershub.charlws.com/atm/dlog/detail?logid=" + String(logid),
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
                userid = d.userid;
                name = d.name;
                d = d.data;
                if (d.type == "job.delivered") {
                    d = d.data.object;
                    planned_distance = TSeparator(parseInt(d.planned_distance / 1.6)) + "Mi";
                    fuel_used_org = d.fuel_used;
                    fuel_used = TSeparator(parseInt(d.fuel_used)) + "L";
                    cargo = d.cargo.name;
                    cargo_mass = TSeparator(parseInt(d.cargo.mass)) + "kg";
                    source_company = "Unknown company";
                    source_city = "Unknown city";
                    destination_company = "Unknown company";
                    destination_city = "Unknown city";
                    if(d.source_company != null) source_company = d.source_company.name;
                    if(d.source_city != null) source_city = d.source_city.name;
                    if(d.destination_company != null) destination_company = d.destination_company.name;
                    if(d.destination_city != null) destination_city = d.destination_city.name;
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
                    meta = d.events[d.events.length - 1].meta;
                    revenue = TSeparator(meta.revenue);
                    earned_xp = meta.earned_xp;
                    cargo_damage = meta.cargo_damage;
                    distance = TSeparator(parseInt(meta.distance / 1.6)) + "Mi";
                    auto_park = meta.auto_park;
                    auto_load = meta.auto_load;
                    avg_fuel = TSeparator(parseInt(fuel_used_org / (distance / 1.6) * 100));

                    info = "<div style='text-align:left'><p><b>From</b>: " + source_city + "</p>";
                    info += "<p><b>To</b>: " + destination_city + "</p>";
                    info += "<p><b>Cargo</b>: " + cargo + "</p>";
                    info += "<p><b>Weight</b>: " + cargo_mass + "</p>";
                    info += "<p><b>Initial Company</b>: " + source_company + "</p>";
                    info += "<p><b>Target Company</b>: " + destination_company + "</p>";
                    info += "<p><b>Planned Distance</b>: " + planned_distance + "</p>";
                    info += "<p><b>Driven Distance</b>: " + distance + "</p>";
                    info += "<p><b>Profit</b>: " + revenue + " " + punit + "</p>";
                    info += "<p><b>XP</b>: " + earned_xp + "</p>";
                    info += "<p><b>Damage</b>: " + parseInt(cargo_damage * 100) + "%</p>";
                    info += "<p><b>Truck</b>: " + truck + "</p>";
                    info += "<p><b>Truck's License Plate</b>: " + license_plate + "</p>";
                    info += "<p><b>Trailer's License Plate" + trs + "</b>: " + trailer.slice(0, -3) + "</p>";
                    info += "<p><b>Average Consumption</b>: " + avg_fuel + "L/100Mi</p>";
                    info += "<p><b>Fuel Used</b>: " + fuel_used + "</p>";
                    info += "<p><b>Maximal Reached Speed</b>: " + top_speed + "Mi/h</p>";
                    extra = "";
                    if (auto_park) extra += "Auto Park | ";
                    if (auto_load) extra += "Auto Load | ";
                    if (extra != "") info += "<p>" + extra.slice(0, -3) + "</p>";
                    dt = getDateTime(data.response.timestamp * 1000);
                    info += "<p><b>Time submitted</b>: " + dt + "</p>";
                    info += "</div>";
                    Swal.fire({
                        title: "Delivery Log #" + logid,
                        html: info,
                        icon: 'info',
                        confirmButtonText: 'Close'
                    })
                } else if (d.type == "job.cancelled") {
                    d = d.data.object;
                    planned_distance = TSeparator(parseInt(d.planned_distance / 1.6)) + "Mi";
                    fuel_used_org = d.fuel_used;
                    fuel_used = TSeparator(parseInt(d.fuel_used)) + "L";
                    driven_distance = TSeparator(parseInt(d.driven_distance / 1.6)) + "Mi";
                    driven_distance_org = d.driven_distance;
                    cargo = d.cargo.name;
                    cargo_damage = d.cargo.damage * 100;
                    cargo_mass = TSeparator(parseInt(d.cargo.mass)) + "kg";
                    source_company = d.source_company.name;
                    source_city = d.source_city.name;
                    destination_company = d.destination_company.name;
                    destination_city = d.destination_city.name;
                    truck = d.truck.brand.name + " " + d.truck.name;
                    license_plate = d.truck.license_plate_country.unique_id.toUpperCase() + " " + d.truck.license_plate;
                    top_speed = parseInt(d.truck.top_speed / 1.6);
                    trailer = "";
                    trs = "";
                    if (d.trailers.length > 1) trs = "s";
                    for (var i = 0; i < d.trailers.length; i++) {
                        trailer += d.trailers[i].license_plate_country.unique_id.toUpperCase() + " " + d.trailers[i]
                            .license_plate + " | ";
                    }
                    punit = "€";
                    if (!d.game.short_name.startsWith("e")) punit = "$";
                    meta = d.events[d.events.length - 1].meta;
                    penalty = TSeparator(meta.penalty);
                    avg_fuel = TSeparator(parseInt(fuel_used_org / (driven_distance_org / 1.6) * 100));

                    info = "<div style='text-align:left'><p><b>From</b>: " + source_city + "</p>";
                    info += "<p><b>To</b>: " + destination_city + "</p>";
                    info += "<p><b>Cargo</b>: " + cargo + "</p>";
                    info += "<p><b>Weight</b>: " + cargo_mass + "</p>";
                    info += "<p><b>Initial Company</b>: " + source_company + "</p>";
                    info += "<p><b>Target Company</b>: " + destination_company + "</p>";
                    info += "<p><b>Planned Distance</b>: " + planned_distance + "</p>";
                    info += "<p><b>Driven Distance</b>: " + driven_distance + "</p>";
                    info += "<p><b>Penalty</b>: " + penalty + " " + punit + "</p>";
                    info += "<p><b>Damage</b>: " + parseInt(cargo_damage) + "%</p>";
                    info += "<p><b>Truck</b>: " + truck + "</p>";
                    info += "<p><b>Truck's License Plate</b>: " + license_plate + "</p>";
                    info += "<p><b>Trailer's License Plate" + trs + "</b>: " + trailer.slice(0, -3) + "</p>";
                    info += "<p><b>Average Consumption</b>: " + avg_fuel + "L/100Mi</p>";
                    info += "<p><b>Fuel Used</b>: " + fuel_used + "</p>";
                    info += "<p><b>Maximal Reached Speed</b>: " + top_speed + "Mi/h</p>";
                    dt = getDateTime(data.response.timestamp * 1000);
                    info += "<p><b>Time submitted</b>: " + dt + "</p>";
                    info += "</div>";
                    Swal.fire({
                        title: "Job Cancelled #" + logid,
                        html: info,
                        icon: 'error',
                        confirmButtonText: 'Close'
                    })
                }

            }
            $("#DeliveryInfoBtn" + logid).removeAttr("disabled");
            $("#DeliveryInfoBtn" + logid).html("Show Details");
        },
        error: function (data) {
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

function loadEvent() {
    page = $("#epages").val();
    if (page == "") page = 1;
    if (page == undefined) page = 1;
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
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                return;
            }
            $("#eventTableHead").show();
            $("#etotpages").html(Math.ceil(data.response.tot / 10));
            for (i = 0; i < events.length; i++) {
                const event = events[i];
                allevents[event.eventid] = event;
                mts = event.mts * 1000;
                dts = event.dts * 1000;
                now = +new Date();
                color = "black";
                if (now >= mts - 1000 * 60 * 60 * 6) {
                    color = "blue";
                }
                if (now >= mts && now <= dts + 1000 * 60 * 30) {
                    color = "green"
                }
                if (now > dts + 1000 * 60 * 30) {
                    color = "grey";
                }
                mt = getDateTime(mts);
                dt = getDateTime(dts);
                $("#eventTable").append(`
            <tr class="text-xs bg-gray-50" style="color:${color}">
              <td class="py-5 px-6 font-medium">${event.eventid}</td>
              <td class="py-5 px-6 font-medium">${event.title}</td>
              <td class="py-5 px-6 font-medium">${event.departure}</td>
              <td class="py-5 px-6 font-medium">${event.destination}</td>
              <td class="py-5 px-6 font-medium">${event.distance}</td>
              <td class="py-5 px-6 font-medium">${mt}</td>
              <td class="py-5 px-6 font-medium">${dt}</td>
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

function eventDetail(eventid) {
    keys = Object.keys(allevents);
    if (keys.indexOf(eventid) == -1) return toastFactory("error", "Error:", "Event not found.", 5000, false);
    event = allevents[eventid];
    info = `<div style="text-align:left">`;
    info += "<p><b>Event ID</b>: " + event.eventid + "</p>";
    info += "<p><b>From</b>: " + event.departure + "</p>";
    info += "<p><b>To</b>: " + event.destination + "</p>";
    info += "<p><b>Distance</b>: " + event.distance + "</p>";
    info += "<p><b>Start Time</b>: " + getDateTime(event.mts * 1000) + "</p>";
    info += "<p><b>End Time</b>: " + getDateTime(event.dts * 1000) + "</p>";
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

function loadMembers() {
    page = $("#mpages").val();
    if (page == "") page = 1;
    if (page == undefined) page = 1;
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
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                return;
            }
            $("#membersTableHead").show();
            $("#mtotpages").html(Math.ceil(data.response.tot / 10));
            for (i = 0; i < users.length; i++) {
                const user = users[i];
                // Fill the table using this format: 
                // <tr class="text-xs bg-gray-50">
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
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">${user.userid}</td>
              <td class="py-5 px-6 font-medium" style="color:${color}">
                <a style="cursor:pointer;" onclick="loadProfile('${user.userid}')">
                <img src='${src}' width="20px" style="display:inline;border-radius:100%"> ${user.name}</a></td>
              <td class="py-5 px-6 font-medium" style="color:${color}">${highestrole}</td>
            </tr>`)
            }
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

function loadAuditLog() {
    page = $("#auditpages").val();
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
        <tr class="text-xs bg-gray-50">
          <td class="py-5 px-6 font-medium">No Data</td>
          <td class="py-5 px-6 font-medium"></td>
          <td class="py-5 px-6 font-medium"></td>
        </tr>`);
                return;
            }
            $("#auditTableHead").show();
            $("#audittotpages").html(Math.ceil(data.response.tot / 30));
            for (i = 0; i < audits.length; i++) {
                audit = audits[i];
                dt = getDateTime(audit.timestamp * 1000);
                op = parseMarkdown(audit.operation).replace("\n", "<br>");
                $("#auditTable").append(`
        <tr class="text-xs bg-gray-50">
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
            d = data.response.list;
            if (d.length == 0) {
                return toastFactory("error", "Error:", "No member with name " + val + " found.", 5000, false);
            }
            userid = d[0].userid;

            $.ajax({
                url: "https://drivershub.charlws.com/atm/member/info?userid=" + String(userid),
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
                        lastfetch = userid;
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

function loadUserDelivery() {
    page = $("#udpages").val();
    if (page == "") page = 1;
    if (page == undefined) page = 1;
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
        url: "https://drivershub.charlws.com/atm/dlog/list?quserid=" + curprofile + "&speedlimit=" + speedlimit + "&page=" + page + "&starttime=" + starttime + "&endtime=" + endtime,
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
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                return;
            }
            $("#userDeliveryTableHead").show();
            $("#udtotpages").html(Math.ceil(data.response.tot / 10));
            for (i = 0; i < deliveries.length; i++) {
                const delivery = deliveries[i];
                // Fill the table using this format: 
                // <tr class="text-xs bg-gray-50">
                //  <td class="py-5 px-6 font-medium">id here</td>
                //    <td class="py-5 px-6 font-medium">name here</td>
                //  </tr>
                //
                distance = TSeparator(parseInt(delivery.distance / 1.6));
                cargo_mass = parseInt(delivery.cargo_mass / 1000);
                unittxt = "€";
                if (delivery.unit == 2) unittxt = "$";
                profit = TSeparator(delivery.profit);
                color = "black";
                if (delivery.profit < 0) color = "grey";
                dtl = "";
                if (localStorage.getItem("token") != "guest") {
                    dtl =
                        `<td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:grey" id="DeliveryInfoBtn${delivery.logid}" onclick="deliveryDetail('${delivery.logid}')">Show Details</td>`;
                }
                $("#userDeliveryTable").append(`
            <tr class="text-xs bg-gray-50" style="color:${color}">
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
    $("#udpages").val("1");
    curprofile = userid;
    loadUserDelivery(userid);
    tabname = "#ProfileTab";
    $(".tabs").hide();
    $(tabname).show();
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
                for (var i = 0; i < roles.length; i++) {
                    if (roles[i] == 0) color = "black";
                    else if (roles[i] < 10) color = "#770202";
                    else if (roles[i] <= 98) color = "#ff0000";
                    else if (roles[i] == 99) color = "#4e6f7b";
                    else if (roles[i] == 100) color = "#b30000";
                    else if (roles[i] > 100) color = "grey";
                    if (rolelist[roles[i]] != undefined) rtxt += `<span class='tag' style='max-width:fit-content;display:inline;background-color:${color}'>` + rolelist[roles[i]] + "</span> ";
                    else rtxt += "Unknown Role (ID " + roles[i] + "), ";
                }
                rtxt = rtxt.substring(0, rtxt.length - 2);
                info += "<h1 style='font-size:40px'>" + d.name + "</h1>";
                info += "<p><b>User ID:</b> " + d.userid + "</p>"
                info += "<p><b>Roles:</b> " + rtxt + "</p>";
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
            $("#HomeTabBtn").click();
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


function loadUsers() {
    page = $("#pupages").val();
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
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                return;
            }
            $("#usersTableHead").show();
            $("#putotpages").html(Math.ceil(data.response.tot / 10));
            for (i = 0; i < users.length; i++) {
                const user = users[i];
                // Fill the table using this format: 
                // <tr class="text-xs bg-gray-50">
                //  <td class="py-5 px-6 font-medium">id here</td>
                //    <td class="py-5 px-6 font-medium">name here</td>
                //  </tr>
                //
                $("#usersTable").append(`
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">${user.discordid}</td>
              <td class="py-5 px-6 font-medium">${user.name}</td>
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

function addUser() {
    discordid = $("#adddiscordid").val();
    if (!isNumber(discordid)) {
        return toastFactory("error", "Error:", "Please enter a valid discord id.", 5000, false);
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
            }
            Swal.fire({
                title: d.name,
                html: info,
                icon: 'info',
                confirmButtonText: 'Close'
            })
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
    $.ajax({
        url: "https://drivershub.charlws.com/atm/user/ban",
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

function loadMyApp() {
    page = $("#myapppage").val();
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
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                return;
            }
            $("#myappTableHead").show();
            $("#myapptotpages").html(Math.ceil(data.response.tot / 10));
            for (i = 0; i < applications.length; i++) {
                const application = applications[i];
                // Fill the table using this format: 
                // <tr class="text-xs bg-gray-50">
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
                if (application.status == 1) color = "green";
                if (application.status == 2) color = "red";

                $("#myappTable").append(`
            <tr class="text-xs bg-gray-50">
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

function loadAllApp() {
    page = $('#allapppage').val();
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
            <tr class="text-xs bg-gray-50">
              <td class="py-5 px-6 font-medium">No Data</td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
              <td class="py-5 px-6 font-medium"></td>
            </tr>`);
                return;
            }
            $("#allappTableHead").show();
            for (i = 0; i < applications.length; i++) {
                const application = applications[i];
                // Fill the table using this format: 
                // <tr class="text-xs bg-gray-50">
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
                if (application.status == 1) color = "green";
                if (application.status == 2) color = "red";

                $("#allappTable").append(`
            <tr class="text-xs bg-gray-50" id="AllApp${application.applicationid}">
              <td class="py-5 px-6 font-medium">${application.applicationid}</td>
              <td class="py-5 px-6 font-medium">${application.name}</td>
              <td class="py-5 px-6 font-medium">${apptype}</td>
              <td class="py-5 px-6 font-medium">${creation}</td>
              <td class="py-5 px-6 font-medium" style="color:${color}">${status}</td>
              <td class="py-5 px-6 font-medium">${closedat}</td>
              <td class="py-5 px-6 font-medium"><a style="cursor:pointer;color:grey" id="AllAppBtn${application.applicationid}" onclick="appDetail(${application.applicationid})">Show Details</td>
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

function appDetail(applicationid) {
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
                    }
                    Swal.fire({
                        title: apptype + ' Application #' + applicationid,
                        html: info + ret.replaceAll("\n", "<br>"),
                        icon: 'info',
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

$(document).ready(function () {
    loadStats();
    setInterval(loadStats, 60000);

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
    devwarn();
    $("body").keydown(function (e) {
        var keyCode = e.keyCode || e.which;
        if (keyCode == 123) {
            devwarn();
        }
    });

    validate();

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
                $("#HomeTabLeft").append(banner.replaceAll("py-8 ", ""));
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
        }
    });
    $("#annloadmore").click(function () {
        $.ajax({
            url: "https://drivershub.charlws.com/atm/announcement?page=" + annpage,
            type: "GET",
            dataType: "json",
            headers: {
                "Authorization": "Bearer " + token
            },
            success: function (data) {
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
                }
                if (ann.length == 0) {
                    toastFactory("info", "No more announcements", "You have reached the end of the list", 5000,
                        false);
                    $("#annloadmore").attr("disabled", "disabled");
                }
            }
        });
    });
});