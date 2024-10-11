function init() {
    python service/manage.py migrate
}

function run_tests() {
    pytest -s
}

function reset_db() {
    python service/manage.py reset_db --noinput -c
}

if [[ $ENV = 'testing' ]]; then
    init 0
    run_tests 0
    test_exit_code=$?
    i=0
    while [[ $test_exit_code -eq 137 && $i -lt 3 ]]
    do
        run_tests 0
        test_exit_code=$?
        i=$(($i+1))
    done
    reset_db 0
    [[ $test_exit_code -eq 0 ]] && exit 0 || exit 1
else
    echo "Can't run tests in a non-testing environment"
    echo "Env: $ENV"
fi