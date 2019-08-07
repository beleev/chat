var backend = "http://127.0.0.1:8080"
var info = JSON.parse("{\"topics\": [], \"messages\": []}")
var uid = ""

function adduser() {
    $("#user").append("<tr>" +
        "<th scope=\"row\">" + ($("#user").children().length + 1) + "</th>" +
        "<td><input class=\"mr-sm-2\" type=\"text\" name=\"user\"/></td>" +
        "</tr>")
}

function adduserbyval(value) {
    $("#user").append("<tr>" +
        "<th scope=\"row\">" + ($("#user").children().length + 1) + "</th>" +
        "<td><input class=\"mr-sm-2\" type=\"text\" name=\"user\" value=" + value + "></td>" +
        "</tr>")
}

function deluser() {
    $('#user').children().last().remove()
}

function addgroup() {
    $("#group").append("<tr>" +
        "<th scope=\"row\">" + ($("#group").children().length + 1) + "</th>" +
        "<td><input class=\"mr-sm-6\" type=\"text\" name=\"group\"/></td>" +
        "<td><button class=\"btn btn-primary\" onclick=\"addmember(this)\">添加成员</button>" +
        "<button class=\"btn btn-danger\" onclick=\"delmember(this)\">删除成员</button></td>" +
        "</tr>")
}

function addgroupbyvalue(name, userlist) {
    ele = "<tr>" +
    "<th scope=\"row\">" + ($("#group").children().length + 1) + "</th>" +
    "<td><input class=\"mr-sm-6\" type=\"text\" name=\"group\" va" +
        "lue=" + name + "></td>" +
    "<td><button class=\"btn btn-primary\" onclick=\"addmember(this)\">添加成员</button>";

    for (var i=0; i<userlist.length; i++) {
        ele += "<select class=\"browser-default custom-select mr-sm-2\" name=\"member\"><option selected>" +
            userlist[i] + "</option>"

        $('#user').children().each(function() {
            if ($(this).find("input").val() && userlist[i] != $(this).find("input").val()) {
                ele += "<option>" + $(this).find("input").val() + "</option>"
            }
        })
        ele += "</select>"
    }

    ele += "<button class=\"btn btn-danger\" onclick=\"delmember(this)\">删除成员</button></td></tr>"

    $("#group").append(ele)
}

function addmember(elem) {
    sel = "<select class=\"browser-default custom-select mr-sm-2\" name=\"member\"><option selected>选择成员</option>"
    $('#user').children().each(function() {
        if ($(this).find("input").val()) {
            sel += "<option>" + $(this).find("input").val() + "</option>"
        }
    })
    sel += "</select>"
    $(elem).after(sel)
}

function delmember(elem) {
    $(elem).siblings("select").last().remove()
}

function delgroup() {
    $('#group').children().last().remove()
}

function genesender() {

    var ret = "<select class=\"browser-default custom-select\">" +
        "<option selected>选择发送者</option>"

    $('#user').children().each(function() {
        if ($(this).find("input").val()) {
            ret += "<option>" + $(this).find("input").val() + "</option>"
        }
    })

    ret += "</select>"
    return ret
}

function generecver() {

    var ret = "<select class=\"browser-default custom-select\">" +
        "<option selected>选择接收者</option>"

    $('#group').children().each(function() {
        if ($(this).find("input").val()) {
            ret += "<option>" + $(this).find("input").val() + "</option>"
        }
    })

    ret += "<option>测评人</option>"
    ret += "</select>"
    return ret
}

function addmessage() {
    $("#message").append("<tr>" +
        "<th scope=\"row\">" + ($("#message").children().length + 1) + "</th>" +
        "<td>" + genesender() + "</td>" +
        "<td>" + generecver()  + "</td>" +
        "<td><input class=\"mr-sm-2\" type=\"text\" name=\"time\"/></td>" +
        "<td><textarea class=\"form-control mr-sm-2\" type=\"text\" name=\"message\"/></td>" +
        "</tr>")
}

function genesenderbyvalue(name) {

    var ret = "<select class=\"browser-default custom-select\">" +
        "<option selected>" + name + "</option>"

    $('#user').children().each(function() {
        if ($(this).find("input").val() && name != $(this).find("input").val()) {
            ret += "<option>" + $(this).find("input").val() + "</option>"
        }
    })

    ret += "</select>"
    return ret
}

function generecverbyvalue(name) {

    var ret = "<select class=\"browser-default custom-select\">" +
        "<option selected>" + name + "</option>"

    $('#group').children().each(function() {
        if ($(this).find("input").val() && name != $(this).find("input").val()) {
            ret += "<option>" + $(this).find("input").val() + "</option>"
        }
    })

    if ("测评人" != name) {
        ret += "<option>测评人</option>"
    }

    ret += "</select>"
    return ret
}

function addmessagebyvalue(from, to, time, msg) {
    $("#message").append("<tr>" +
        "<th scope=\"row\">" + ($("#message").children().length + 1) + "</th>" +
        "<td>" + genesenderbyvalue(from) + "</td>" +
        "<td>" + generecverbyvalue(to)  + "</td>" +
        "<td><input class=\"mr-sm-2\" type=\"text\" name=\"time\" value=" + time + "></td>" +
        "<td><textarea class=\"form-control mr-sm-2\" type=\"text\" name=\"message\" value=" + msg + ">" + msg +
        "</textarea></td></tr>")
}

function delmsg() {
    $('#message').children().last().remove()
}

function init() {
    var topics = []
    var messages = []
    $("#group").children().each(function () {
        var topic = JSON.parse("{}")
        var member = new Array()
        $(this).find("select").each(function () {
            if (!member.includes($(this).val())) {
                member.push($(this).val())
            }
        })
        topic['name'] = $(this).find("input").val()
        topic["member"] = member
        topics.push(topic)
    })
    $("#message").children().each(function () {
        var message = JSON.parse("{}")
        var from = $(this).find("select").eq(0).val()
        var to = $(this).find("select").eq(1).val()
        if ("选择发送者" != from && "选择接收者" != to) {
            message["from"] = from
            if ("测评人" != to) {
                message["to"] = to
            }
            message["message"] = $(this).find("textarea").val()
            var timenum = $(this).find("input").val()
            if (!isNaN(parseInt(timenum))) {
                message["time"] = timenum
                messages.push(message)
            }
        }
    })
    info["topics"] = topics
    info["messages"] = messages

    var test = JSON.stringify(info)
    var url = backend + '/api/init';
    $.ajax({url: url,
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(info),
        dataType: 'json'})
        .done(function(msg) {
            if ("ok" == msg["msg"]) {
                uid = msg["user"]
                $('#chatmsg').html(
                    "初始化完成，进入网址 <b>" + msg["chat"] + "</b> 并使用用户名&密码：<b>" + msg["user"] + "</b> 登录"
                )
            } else {
                $('#chatmsg').html("初始化失败，点击按钮以重试")
            }
        });
}

function start() {
    var url = backend + '/api/start';
    if ("" == uid) {
        alert("请先初始化")
        return
    }
    var data = {"id": uid}
    $.ajax({url: url,
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        dataType: 'json'})
        .done(function(msg) {
            if ("ok" == msg["msg"]) {
                $('#chatmsg').html(
                    "用户名：<b>" + uid + "</b> 测评已开始"
                )
            } else {
                $('#chatmsg').html("启动失败，点击按钮以重试")
            }
        });
}

function stop() {
    var url = backend + '/api/stop';
    if ("" == uid) {
        alert("请先初始化")
        return
    }
    var data = {"id": uid}
    $.ajax({url: url,
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        dataType: 'json'})
        .done(function(msg) {
            if ("ok" == msg["msg"]) {
                $('#chatmsg').html(
                    "用户名：<b>" + uid + "</b> 测评已停止"
                )
            } else {
                $('#chatmsg').html("停止失败，点击按钮以重试")
            }
        });
}

function createAndDownloadFile() {
    var ret = JSON.parse("{\"users\": [], \"topics\": [], \"messages\": []}")
    var users = []
    var topics = []
    var messages = []
    $("#user").children().each(function () {
        $(this).find("input").each(function () {
            if (!users.includes($(this).val())) {
                users.push($(this).val())
            }
        })
    })
    $("#group").children().each(function () {
        var topic = JSON.parse("{}")
        var member = new Array()
        $(this).find("select").each(function () {
            if (!member.includes($(this).val())) {
                member.push($(this).val())
            }
        })
        topic['name'] = $(this).find("input").val()
        topic["member"] = member
        topics.push(topic)
    })
    $("#message").children().each(function () {
        var message = JSON.parse("{}")
        var from = $(this).find("select").eq(0).val()
        var to = $(this).find("select").eq(1).val()
        message["from"] = from
        message["to"] = to
        message["message"] = $(this).find("textarea").val()
        var timenum = $(this).find("input").val()
        message["time"] = timenum
        messages.push(message)
    })
    ret["users"] = users
    ret["topics"] = topics
    ret["messages"] = messages

    var aTag = document.createElement('a');
    var out = JSON.stringify(ret)
    var blob = new Blob([out]);
    aTag.download = "save.txt";
    aTag.href = URL.createObjectURL(blob);
    aTag.click();
    URL.revokeObjectURL(blob);
}

function loadFile(files) {
    if (files.length) {
        for (let i in files) {
            let file = files[i];
            console.log(file);
            let reader = new FileReader();
            reader.onload = function () {
                console.log(this.result)
                var into = JSON.parse(this.result)
                info["topics"] = into["topics"]
                info["messages"] = into["messages"]

                for (var i=0; i<into["users"].length; i++) {
                    adduserbyval(into["users"][i])
                }
                for (var i=0; i<into["topics"].length; i++) {
                    addgroupbyvalue(into["topics"][i]["name"], into["topics"][i]["member"])
                }
                for (var i=0; i<into["messages"].length; i++) {
                    addmessagebyvalue(into["messages"][i]["from"], into["messages"][i]["to"],
                        into["messages"][i]["time"], into["messages"][i]["message"])
                }

            };
            reader.readAsText(file);
        }
    }
}
