// --- MathQuill Supplemental
function make_math_field(target) {  // Takes a jquery selector for an input
    let parent = target.parents().eq(0);
    $(target).replaceWith(`<span class="math-field">${$(target).val()}</span>`);
    let answerSpan = parent.find('.math-field').get(0);
    MQ.MathField(answerSpan, {
        autoCommands: 'alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega sum prod int sqrt nthroot vec times div pm circ infinity',
        handlers: {
            edit: function(mathField) {
                let latex = mathField.latex();
                if (latex.includes('->')) {
                    mathField.latex(latex.replace('->', '\\rightarrow '));
                } else if (latex.includes('=>')) {
                    mathField.latex(latex.replace('=>', '\\Rightarrow '));
                }
            }
        }
    });
}

function convert_to_regular_field(target) {
    target.replaceWith(`<input type="text" autocomplete="off" class="card-text" value="${MQ.MathField(target.get(0)).latex()}">`);
}

function reset_sr_input() {
    let target = $("#answer-prompt .math-field");
    target.replaceWith(`<input id="prompt-response" placeholder="Type your answer here" autocomplete="off" value="">`);
}

function reset_mcq_options() {
    let targets = $("#answer-buttons p .option-text");
    targets.each(function (i) {
        targets.eq(i).replaceWith(`<span class="option-text">Option</span>`);
    })
}


// -- Convert to MathQuill
function convertMQ() {
    let to_convert = $(".convertMQ");
    to_convert.each(function (i) {
        to_convert.eq(i).removeClass('convertMQ');
        MQ.StaticMath(to_convert.get(i));
    });
    to_convert = $(".convertMQ_edit");
    to_convert.each(function (i) {
        make_math_field(to_convert.eq(i));
    });
}
// --x