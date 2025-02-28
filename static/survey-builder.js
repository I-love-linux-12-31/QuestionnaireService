let questionCounter = 0;

function addQuestion() {
    const container = document.getElementById('questions-container');
    const questionHTML = `
        <div class="card mb-3 question-card" data-qid="${questionCounter}">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Вопрос #${questionCounter + 1}</h5>
                <button type="button" class="btn btn-danger btn-sm" onclick="this.closest('.question-card').remove()">
                    Удалить
                </button>
            </div>
            <div class="card-body">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label class="form-label">Текст вопроса</label>
                        <input type="text" 
                               name="questions[${questionCounter}][text]" 
                               class="form-control" 
                               required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Тип вопроса</label>
                        <select name="questions[${questionCounter}][type]" 
                                class="form-select question-type" 
                                onchange="updateQuestionOptions(${questionCounter})">
                            <option value="text">Текст</option>
                            <option value="single_choice">Один вариант</option>
                            <option value="multiple_choice">Несколько вариантов</option>
                            <option value="limited_choice">Лимитированный выбор</option>
                            <option value="file">Файл</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <div class="form-check mt-4 pt-2">
                            <input type="checkbox" 
                                   name="questions[${questionCounter}][required]" 
                                   id="required-${questionCounter}" 
                                   class="form-check-input">
                            <label class="form-check-label" for="required-${questionCounter}">Обязательный</label>
                        </div>
                    </div>
                </div>

                <div class="question-options" id="options-${questionCounter}">
                    <!-- Здесь появятся варианты ответов -->
                </div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', questionHTML);
    questionCounter++;
}

function updateQuestionOptions(qIndex) {
    const type = document.querySelector(`[name="questions[${qIndex}][type]"]`).value;
    const optionsContainer = document.getElementById(`options-${qIndex}`);
    optionsContainer.innerHTML = '';

    if (['single_choice', 'multiple_choice', 'limited_choice'].includes(type)) {
        const optionsHTML = `
            <div class="mb-3">
                <label class="form-label">Варианты ответов</label>
                <div class="options-list">
                    <div class="input-group mb-2">
                        <input type="text" 
                               name="questions[${qIndex}][options][]" 
                               class="form-control">
                        <button type="button" 
                                class="btn btn-outline-secondary" 
                                onclick="addOption(this)">
                            +
                        </button>
                    </div>
                </div>
            </div>
            ${type === 'limited_choice' ? `
            <div class="col-md-3">
                <label class="form-label">Лимит выборов</label>
                <input type="number" 
                       name="questions[${qIndex}][limit]" 
                       class="form-control" 
                       min="1" 
                       value="1">
            </div>` : ''}
        `;
        optionsContainer.innerHTML = optionsHTML;
    }
}

function addOption(btn) {
    const optionsList = btn.closest('.options-list');
    const newOption = document.createElement('div');
    newOption.className = 'input-group mb-2';
    newOption.innerHTML = `
        <input type="text" 
               name="${btn.previousElementSibling.name}" 
               class="form-control">
        <button type="button" 
                class="btn btn-outline-danger" 
                onclick="this.parentElement.remove()">
            &times;
        </button>
    `;
    optionsList.appendChild(newOption);
}