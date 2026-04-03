<?php
// ================================================
// Drawing Management System API
// PHP 5.6 Compatible
// ================================================

ini_set('display_errors', 1);
error_reporting(E_ALL);

// Go to root folder
chdir('../../');

// Include required files
require_once('includes/db/mysql/query_factory.php');
require_once('my_files/dev_microerp/config.php');     // Contains DB_SERVER, DB_DATABASE etc.

$db = new queryFactory();

$connected = $db->connect(
    DB_SERVER_HOST,      // Host
    DB_SERVER_USERNAME,  // Username
    DB_SERVER_PASSWORD,  // Password
    'dev_microerp'       // Database name
);

$OUTPUT = array();

$action = isset($_REQUEST['action']) ? trim($_REQUEST['action']) : '';

// ------------------------------------------------
// ACTION: login
// Method: POST
// Params: username, password
// ------------------------------------------------
if ($action === 'login') {

    $username = isset($_REQUEST['username']) ? trim($_REQUEST['username']) : '';
    $password = isset($_REQUEST['password']) ? trim($_REQUEST['password'])  : '';

    // Validate inputs
    if ($username === '' || $password === '') {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Username and password are required.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // MD5 hash the incoming password
    $password_md5 = md5($password);

    // Query user table — adjust table/column names to match your DB schema
    $sql = "SELECT emp_id, emp_name, username, dept, designation
            FROM users
            WHERE username = '" . $db->Escape($username) . "'
              AND password = '" . $password_md5 . "'
            LIMIT 1";

    $result = $db->Execute($sql);

    if ($result && !$result->EOF) {
        $user = $result->fields;

        $OUTPUT['response']    = 'true';
        $OUTPUT['message']     = 'Login successful.';
        $OUTPUT['data']        = array(
            'emp_id'      => $user['emp_id'],
            'emp_name'    => $user['emp_name'],
            'username'    => $user['username'],
            'dept'        => $user['dept'],
            'designation' => $user['designation'],
        );
    } else {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Invalid username or password.';
        $OUTPUT['data']     = array();
    }

// ------------------------------------------------
// ACTION: get_inventory (example / default)
// ------------------------------------------------
} elseif ($action === 'get_inventory') {

    $sql = "SELECT * FROM inventory LIMIT 10";

    $result = $db->Execute($sql);

    $data = array();
    while (!$result->EOF) {
        $data[] = $result->fields;
        $result->MoveNext();
    }

    $OUTPUT['response'] = 'true';
    $OUTPUT['message']  = 'OK';
    $OUTPUT['total']    = count($data);
    $OUTPUT['data']     = $data;

// ------------------------------------------------
// Unknown / missing action
// ------------------------------------------------
} else {

    $OUTPUT['response'] = 'false';
    $OUTPUT['message']  = 'Unknown or missing action.';
    $OUTPUT['data']     = array();

}

header('Content-Type: application/json');
echo json_encode($OUTPUT);
?>
