let set_id = window.location.pathname.split('/')[2];
let options;
let type;
let answered = false;
let MQ = MathQuill.getInterface(2);

$(document).ready(function() {
    getNextQuestion();
    $("#answer-buttons p").on("click", function () {
        if (!answered) {
            let id = $(this).attr('id');  // Using 'this' = container, event.target can return the children
            submit_answer_mcq(id);
        }
    });
    $("#study").on('keyup',function(event) {
        if (!answered) {
            if (event.which == 13) {
                setTimeout(submit_answer_prompt, 50);
            }
        }
    });
    $("#prompt-submit").on('click',function(event) {
        if (!answered) {
            submit_answer_prompt();
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
        $("#advance-ready").hide();
        $("#question h3").replaceWith("<h3>" + data["question"].replace('@@MQ@@', '') + "</h3>");
        if (data["question"].startsWith("@@MQ@@")) {
            $("#question h3").addClass('convertMQ');
        }
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
            reset_mcq_options();
            for (let key in options) {
                $("#answer #answer-buttons p .material-symbols-outlined").eq(counter).text(`counter_${counter+1}`);
                $("#answer #answer-buttons p .option-text").eq(counter).text(options[key].replace("@@MQ@@", ''));
                $("#answer #answer-buttons p").eq(counter).attr('id', key);
                $("#answer #answer-buttons p").eq(counter).show();
                if (options[key].startsWith("@@MQ@@")) {
                    $("#answer #answer-buttons p .option-text").eq(counter).addClass("convertMQ");
                }
                counter += 1;
            }
        }
        else {
            $("#answer #answer-buttons").hide();
            $("#answer #answer-prompt").show();
            reset_sr_input();
            $("#answer-prompt input").val("");
            $("#correct-answer").removeClass('incorrect');
            $("#correct-answer").removeClass('correct');
            $("#correct-answer").hide();
            $("#math-help").hide();
            if (data['mathquill']) {
                $("#answer-prompt input").val("");
                make_math_field($("#answer-prompt input"));
                $("#math-help").show();
            }
        }
        convertMQ();
        $("#study").show();
        $("#answer-prompt input").focus();
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
        $("#answer-buttons p span.material-symbols-outlined").text("cancel");
        $(`#answer-buttons #${correct_answer} span.material-symbols-outlined`).text("check_circle");
        $(`#answer-buttons #${correct_answer}`).addClass("correct");
        $("#btn-skip").hide();
        $("#advance-ready").show();
    });
    answered = true;
}

function submit_answer_prompt() {
    let answer
    if ($("#prompt-response").val()) {
        answer = $("#prompt-response").val();
    }
    else if ($('.math-field')) {
        answer = "@@MQ@@" + MQ.MathField($(".math-field").get(0)).latex();
    }
    socket.emit("check_answer", {"set_id": set_id, "answer": answer}, (response) => {
        if (response.status === 401) {
            window.alert("You have been signed out. To continue studying, please sign in again.");
        }
        let correct_answer = response['correct'];
        if (correct_answer.startsWith("@@MQ@@")) {
            correct_answer = "<span class='convertMQ'>" + correct_answer.replace("@@MQ@@", "") + "</span>"
        }
        if (response['success']) {
            if (response['accuracy'] !== 100) {
                $("#correct-answer").html(`Close enough. The right answer was: "${correct_answer}"`);
            }
            else {
                $("#correct-answer").text("Correct!");
            }
            $("#correct-answer").addClass('correct');
        }
        else {
            $("#correct-answer").html(`Sorry. The right answer was: "${correct_answer}"`);
            $("#correct-answer").addClass('incorrect');
        }
        convertMQ();
        $("#correct-answer").show();
        $("#btn-skip").hide();
        $("#advance-ready").show();
    });
    answered = true;
}


// Submit via button
$(document).ready(function() {
    $('body').on("keyup", function (e) {
        if (answered) {
            e.preventDefault();
            getNextQuestion();
        }
        else if (49 <= e.keyCode <= 52) {
            if (type === 'mc') {
                e.preventDefault();
                let id = $("#answer-buttons p").eq(e.keyCode - 49).prop("id");
                submit_answer_mcq(id);
            }
        }
    });
});