let set_id = window.location.pathname.split('/')[2];
let options
let socket;
let type;
let answered = false;

$(document).ready(function() {
    socket = io.connect(location.protocol + "//" + document.domain + ':' + location.port);
    getNextQuestion();
    $("#answer-buttons p").on("click", function (event) {
        if (!answered) {
            let id = $(event.target).attr('id');
            submit_answer_mcq(id);
        }
    });
    $("#prompt-response").on('keypress',function(event) {
        if (!answered) {
            if (event.which == 13) {
                submit_answer_prompt($("#prompt-response").val());
            }
        }
    });
    $("#prompt-submit").on('click',function(event) {
        if (!answered) {
            submit_answer_prompt($("#prompt-response").val());
        }
    });
});

function getNextQuestion() {
    window.location.href = '#top';
    let data;
    socket.emit("study_next", {"set_id": set_id}, (response) => {
        data = response;
        type = data['type']
        if (response.status === 401) {
            $("#header-login-button").click();  // Login and then redirect user
        }
        $("#loading").hide();
        $("#btn-skip").show();
        $("#btn-next").hide();
        $("#question h3").text(data["question"]);
        $("#current-round span").text(response["round"]);
        if (data["side"] === "back") {
            $("#answer-side").removeClass("cp-definition");
            $("#answer-side").addClass("cp-term");
            $("#answer-side").text("Term");
            $("#question-side").removeClass("cp-term");
            $("#question-side").addClass("cp-definition");
            $("#question-side").text("Definition");
        }
        else {
            $("#question-side").removeClass("cp-definition");
            $("#question-side").addClass("cp-term");
            $("#question-side").text("Term");
            $("#answer-side").removeClass("cp-term");
            $("#answer-side").addClass("cp-definition");
            $("#answer-side").text("Definition");
        }
        if (type === "mc") {
            $("#answer #answer-buttons").show();
            $("#answer #answer-prompt").hide();
            options = data["options"];
            let counter = 0;
            $("#answer-buttons p").removeClass("incorrect");
            $("#answer-buttons p").removeClass("correct");
            $("#answer-buttons p").hide();
            for (let key in options) {
                $("#answer #answer-buttons p").eq(counter).html(`<span class="material-symbols-outlined">counter_${counter+1}</span> ${options[key]}`);
                $("#answer #answer-buttons p").eq(counter).attr('id', key);
                $("#answer #answer-buttons p").eq(counter).show();
                counter += 1;
            }
        }
        else {
            $("#answer #answer-buttons").hide();
            $("#answer #answer-prompt").show();
            $("#answer-prompt input").val("");
            $("#correct-answer").removeClass('incorrect');
            $("#correct-answer").removeClass('correct');
            $("#correct-answer").hide();
        }
        $("#study").show();
        answered = false;
    });
}


function submit_answer_mcq(answer) {
    socket.emit("check_answer", {"set_id": set_id, "card_id": answer}, (response) => {
        if (response.status === 401) {
            window.alert("You have been signed out. To continue studying, please sign in again.");
        }
        let correct_answer
        if (response['success']) {
            correct_answer = answer;
        }
        else {
            correct_answer = response['correct'];
            $(`#answer-buttons #${answer}`).addClass("incorrect");
        }
        $("#answer-buttons p span").text("cancel");
        $(`#answer-buttons #${correct_answer} span`).text("check_circle");
        $(`#answer-buttons #${correct_answer}`).addClass("correct");
        $("#btn-skip").hide();
        $("#btn-next").show();
    });
    answered = true;
}

function submit_answer_prompt(answer) {
    socket.emit("check_answer", {"set_id": set_id, "answer": answer}, (response) => {
        if (response.status === 401) {
            window.alert("You have been signed out. To continue studying, please sign in again.");
        }
        let correct_answer = response['correct'];
        if (response['success']) {
            if (response['accuracy'] !== 100) {
                $("#correct-answer").text(`Close enough. The right answer was: "${correct_answer}"`);
            }
            else {
                $("#correct-answer").text("Correct!");
            }
            $("#correct-answer").addClass('correct');
        }
        else {
            $("#correct-answer").text(`Sorry. The right answer was: "${correct_answer}"`);
            $("#correct-answer").addClass('incorrect');
        }
        $("#correct-answer").show();
        $("#btn-skip").hide();
        $("#btn-next").show();
    });
    answered = true;
}
