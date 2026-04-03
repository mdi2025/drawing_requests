<?php
// ================================================
// Drawing Management System API
// PHP 5.6 Compatible
// URL: http://dev.erp.micro/api/DRAWING_MANAGEMENT_SYSTEM/new_app.php
// ================================================

ini_set('display_errors', 1);
error_reporting(E_ALL);

// Go to root folder
chdir('../../');

// Include required files
require_once('includes/db/mysql/query_factory.php');
require_once('my_files/dev_microerp/config.php');     // Contains DB_SERVER_HOST, DB_SERVER_USERNAME etc.

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
// Params: username, password (plain text)
// ------------------------------------------------
if ($action === 'login') {

    $username = isset($_REQUEST['username']) ? trim($_REQUEST['username']) : '';
    $password = isset($_REQUEST['password']) ? trim($_REQUEST['password']) : '';

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

    // Query drawing_users table
    $sql = "SELECT id, admin_name, access_tokens
            FROM drawing_users
            WHERE admin_name = '" . $db->Escape($username) . "'
              AND admin_pass  = '" . $password_md5 . "'
              AND is_deleted  = 0
            LIMIT 1";

    $result = $db->Execute($sql);

    if ($result && !$result->EOF) {
        $user = $result->fields;

        // access_tokens is stored as a JSON string in the DB e.g. [1,2,3]
        $access_tokens_raw = isset($user['access_tokens']) ? $user['access_tokens'] : '[]';

        // Decode JSON into array
        $access_tokens = json_decode($access_tokens_raw, true);
        if (!is_array($access_tokens)) {
            $access_tokens = array();
        }

        $OUTPUT['response']      = 'true';
        $OUTPUT['message']       = 'Login successful.';
        $OUTPUT['data']          = array(
            'id'            => $user['id'],
            'username'      => $user['admin_name'],
            'access_tokens' => $access_tokens,
        );
    } else {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Invalid username or password.';
        $OUTPUT['data']     = array();
    }

// ------------------------------------------------
// ACTION: get_drawing_requests
// Method: GET or POST
// Params: (none required)
// Returns: list of drawings with their latest request status
// ------------------------------------------------
} elseif ($action === 'get_drawing_requests') {

    $sql = "
        SELECT
            m.catalog         AS no,
            m.revision        AS rev,
            m.approved_status AS status,
            m.auto_id         AS id,
            CASE
                WHEN r.status IN ('Pending', 'Issued', 'Returned') THEN
                    CONCAT(u.admin_name, ' at ', DATE_FORMAT(r.requested_at, '%d-%m-%Y %H:%i:%s'))
                ELSE NULL
            END AS requested_by,
            CASE WHEN r.status IN ('Received', 'Rejected') THEN NULL ELSE r.status      END AS req_status,
            CASE WHEN r.status IN ('Received', 'Rejected') THEN NULL ELSE r.bag_name    END AS bag_name,
            CASE WHEN r.status IN ('Received', 'Rejected') THEN NULL ELSE r.ipd_catalog END AS ipd_catalog
        FROM master_data_new m
        JOIN (
            SELECT catalog, MAX(auto_id) AS max_auto_id
            FROM master_data_new
            WHERE approved_status = 'approved'
            GROUP BY catalog
        ) AS t ON m.catalog = t.catalog AND m.auto_id = t.max_auto_id
        LEFT JOIN (
            SELECT r1.drawing_id, r1.revision, r1.requested_by, r1.requested_at,
                   r1.status, r1.bag_name, r1.ipd_catalog
            FROM drawing_requests r1
            JOIN (
                SELECT drawing_id, revision, MAX(requested_at) AS max_ts
                FROM drawing_requests
                GROUP BY drawing_id, revision
            ) r2 ON  r1.drawing_id   = r2.drawing_id
                 AND r1.revision     = r2.revision
                 AND r1.requested_at = r2.max_ts
        ) r ON r.drawing_id = m.catalog AND r.revision = m.revision
        LEFT JOIN drawing_users u ON r.requested_by = u.id
        WHERE r.status IS NULL
           OR r.status = 'Pending'
           OR r.status = 'Issued'
           OR r.status = 'Returned'
           OR r.status = 'Received'
           OR r.status = 'Rejected'
        ORDER BY m.catalog
    ";

    $result = $db->Execute($sql);

    $data = array();
    while ($result && !$result->EOF) {
        $row = $result->fields;
        $data[] = array(
            'id'           => $row['id'],
            'no'           => $row['no'],
            'rev'          => $row['rev'],
            'status'       => $row['status'],
            'requested_by' => $row['requested_by'],
            'req_status'   => $row['req_status'],
            'bag_name'     => $row['bag_name'],
            'ipd_catalog'  => $row['ipd_catalog'],
        );
        $result->MoveNext();
    }

    $OUTPUT['response'] = 'true';
    $OUTPUT['message']  = 'OK';
    $OUTPUT['total']    = count($data);
    $OUTPUT['data']     = $data;

// ------------------------------------------------
// ACTION: insert_drawing_request
// Method: POST
// Params: drawing_id, revision, requested_by, bag_name (optional), ipd_catalog (optional)
// ------------------------------------------------
} elseif ($action === 'insert_drawing_request') {

    $drawing_id = isset($_REQUEST['drawing_id']) ? trim($_REQUEST['drawing_id']) : '';
    $revision = isset($_REQUEST['revision']) ? trim($_REQUEST['revision']) : '';
    $requested_by = isset($_REQUEST['requested_by']) ? (int)$_REQUEST['requested_by'] : 0;
    $bag_name = isset($_REQUEST['bag_name']) ? trim($_REQUEST['bag_name']) : '';
    $ipd_catalog = isset($_REQUEST['ipd_catalog']) ? trim($_REQUEST['ipd_catalog']) : '';

    // Validate required inputs
    if ($drawing_id === '' || $revision === '' || $requested_by <= 0) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Drawing ID, revision, and requested_by are required.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Check for existing pending/issued/returned requests
    $check_sql = "SELECT id, status FROM drawing_requests 
                  WHERE drawing_id = '" . $db->Escape($drawing_id) . "' 
                  AND revision = '" . $db->Escape($revision) . "' 
                  AND status IN ('Pending', 'Issued', 'Returned') 
                  LIMIT 1";
    $check_result = $db->Execute($check_sql);

    if ($check_result && !$check_result->EOF) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'This drawing has already been requested.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Insert new request
    $insert_sql = "INSERT INTO drawing_requests 
                   (drawing_id, revision, requested_by, status, bag_name, ipd_catalog, requested_at) 
                   VALUES ('" . $db->Escape($drawing_id) . "', '" . $db->Escape($revision) . "', " . $requested_by . ", 'Pending', '" . $db->Escape($bag_name) . "', '" . $db->Escape($ipd_catalog) . "', NOW())";

    $insert_result = $db->Execute($insert_sql);

    if ($insert_result) {
        $request_id = $db->Insert_ID();

        // Insert into history
        $history_sql = "INSERT INTO drawing_request_history 
                        (request_id, event_type, performed_by, revision) 
                        VALUES (" . $request_id . ", 'requested', " . $requested_by . ", '" . $db->Escape($revision) . "')";
        $db->Execute($history_sql);

        $OUTPUT['response'] = 'true';
        $OUTPUT['message']  = 'Request submitted successfully.';
        $OUTPUT['request_id'] = $request_id;
    } else {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Failed to submit request.';
    }

// ------------------------------------------------
// ACTION: get_requested_drawings
// Method: GET or POST
// Params: status_filter (optional) - filter by status ('All', 'Pending', 'Issued', 'Rejected', 'Received', 'Returned')
// Returns: list of drawing requests with full details for issuance page
// ------------------------------------------------
} elseif ($action === 'get_requested_drawings') {

    $status_filter = isset($_REQUEST['status_filter']) ? trim($_REQUEST['status_filter']) : 'All';

    $sql = "
        SELECT
            r.id,
            r.drawing_id AS no,
            r.revision AS rev,
            r.status,
            r.bag_name,
            r.ipd_catalog,
            CONCAT(u_req.admin_name, ' at ', DATE_FORMAT(h_req.performed_at, '%d-%m-%Y %H:%i:%s')) AS requested_by,
            CONCAT(u_iss.admin_name, ' at ', DATE_FORMAT(h_iss.performed_at, '%d-%m-%Y %H:%i:%s')) AS issued_info,
            CONCAT(u_rej.admin_name, ' at ', DATE_FORMAT(h_rej.performed_at, '%d-%m-%Y %H:%i:%s')) AS rejected_info,
            h_rej.remarks
        FROM drawing_requests r
        JOIN drawing_request_history h_req
            ON h_req.id = (
                SELECT MAX(id)
                FROM drawing_request_history
                WHERE request_id = r.id
                AND event_type = 'requested'
            )
        JOIN drawing_users u_req ON h_req.performed_by = u_req.id
        LEFT JOIN drawing_request_history h_iss
            ON h_iss.id = (
                SELECT MAX(id)
                FROM drawing_request_history
                WHERE request_id = r.id
                AND event_type = 'issued'
            )
        LEFT JOIN drawing_users u_iss ON h_iss.performed_by = u_iss.id
        LEFT JOIN drawing_request_history h_rej
            ON h_rej.id = (
                SELECT MAX(id)
                FROM drawing_request_history
                WHERE request_id = r.id
                AND event_type = 'rejected'
            )
        LEFT JOIN drawing_users u_rej ON h_rej.performed_by = u_rej.id
        WHERE r.status IN ('Pending', 'open', 'Issued', 'Rejected', 'Returned', 'Received')
        AND (r.status = '" . $db->Escape($status_filter) . "' OR '" . $db->Escape($status_filter) . "' = 'All' OR ('" . $db->Escape($status_filter) . "' = 'Pending' AND r.status = 'open'))
        ORDER BY r.id DESC
        LIMIT 500
    ";

    $result = $db->Execute($sql);

    $data = array();
    while ($result && !$result->EOF) {
        $row = $result->fields;
        $data[] = array(
            'id'            => (int)$row['id'],
            'no'            => $row['no'],
            'rev'           => $row['rev'],
            'status'        => $row['status'],
            'bag_name'      => $row['bag_name'],
            'ipd_catalog'   => $row['ipd_catalog'],
            'requested_by'  => $row['requested_by'],
            'issued_info'   => $row['issued_info'],
            'rejected_info' => $row['rejected_info'],
            'remarks'       => $row['remarks'],
        );
        $result->MoveNext();
    }

    $OUTPUT['response'] = 'true';
    $OUTPUT['message']  = 'OK';
    $OUTPUT['total']    = count($data);
    $OUTPUT['data']     = $data;

// ------------------------------------------------
// ACTION: issue_drawing_request
// Method: POST
// Params: request_id, user_id, target_revision (optional)
// ------------------------------------------------
} elseif ($action === 'issue_drawing_request') {

    $request_id = isset($_REQUEST['request_id']) ? (int)$_REQUEST['request_id'] : 0;
    $user_id = isset($_REQUEST['user_id']) ? (int)$_REQUEST['user_id'] : 0;
    $target_revision = isset($_REQUEST['target_revision']) ? trim($_REQUEST['target_revision']) : '';

    // Validate inputs
    if ($request_id <= 0 || $user_id <= 0) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Request ID and user ID are required.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Check current status
    $status_check = $db->Execute("SELECT status, drawing_id, revision FROM drawing_requests WHERE id = " . $request_id);
    if (!$status_check || $status_check->EOF) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Request not found.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    $current_status = $status_check->fields['status'];
    $drawing_id = $status_check->fields['drawing_id'];
    $current_rev = $status_check->fields['revision'];

    if ($current_status != 'Pending' && $current_status != 'open') {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Request has already been ' . strtolower($current_status) . '.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Check if another request for the same catalog and revision is already issued or returned
    $conflict_check = $db->Execute("SELECT COUNT(*) as count FROM drawing_requests 
                                   WHERE drawing_id = '" . $db->Escape($drawing_id) . "' 
                                   AND revision = '" . $db->Escape($target_revision ?: $current_rev) . "' 
                                   AND status IN ('Issued', 'Returned')");
    if ($conflict_check && $conflict_check->fields['count'] > 0) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Another request for this drawing revision is currently issued or returned.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Update revision if different
    if ($target_revision && $target_revision != $current_rev) {
        $db->Execute("UPDATE drawing_requests SET revision = '" . $db->Escape($target_revision) . "' WHERE id = " . $request_id);
    }

    // Update status
    $update_result = $db->Execute("UPDATE drawing_requests SET status = 'Issued' WHERE id = " . $request_id);

    if ($update_result) {
        // Log history
        $final_revision = $target_revision ?: $current_rev;
        $history_sql = "INSERT INTO drawing_request_history 
                        (request_id, event_type, performed_by, revision) 
                        VALUES (" . $request_id . ", 'issued', " . $user_id . ", '" . $db->Escape($final_revision) . "')";
        $db->Execute($history_sql);

        $OUTPUT['response'] = 'true';
        $OUTPUT['message']  = 'Drawing issued successfully.';
    } else {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Failed to update request status.';
    }

// ------------------------------------------------
// ACTION: reject_drawing_request
// Method: POST
// Params: request_id, user_id, remarks
// ------------------------------------------------
} elseif ($action === 'reject_drawing_request') {

    $request_id = isset($_REQUEST['request_id']) ? (int)$_REQUEST['request_id'] : 0;
    $user_id = isset($_REQUEST['user_id']) ? (int)$_REQUEST['user_id'] : 0;
    $remarks = isset($_REQUEST['remarks']) ? trim($_REQUEST['remarks']) : '';

    // Validate inputs
    if ($request_id <= 0 || $user_id <= 0) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Request ID and user ID are required.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    if ($remarks === '') {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Remarks are required for rejection.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Check current status
    $status_check = $db->Execute("SELECT status FROM drawing_requests WHERE id = " . $request_id);
    if (!$status_check || $status_check->EOF) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Request not found.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    $current_status = $status_check->fields['status'];
    if ($current_status != 'Pending' && $current_status != 'open') {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Request has already been ' . strtolower($current_status) . '.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Update status
    $update_result = $db->Execute("UPDATE drawing_requests SET status = 'Rejected' WHERE id = " . $request_id);

    if ($update_result) {
        // Log history with remarks
        $history_sql = "INSERT INTO drawing_request_history 
                        (request_id, event_type, performed_by, revision, remarks) 
                        VALUES (" . $request_id . ", 'rejected', " . $user_id . ", 
                               (SELECT revision FROM drawing_requests WHERE id = " . $request_id . "), 
                               '" . $db->Escape($remarks) . "')";
        $db->Execute($history_sql);

        $OUTPUT['response'] = 'true';
        $OUTPUT['message']  = 'Request rejected successfully.';
    } else {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Failed to update request status.';
    }

// ------------------------------------------------
// ACTION: get_issued_drawings_for_user
// Method: GET or POST
// Params: user_id, status_filter (optional) - filter by status ('All', 'Pending', 'Issued', 'Returned', 'Received', 'Rejected')
// Returns: list of drawings issued to the user for return
// ------------------------------------------------
} elseif ($action === 'get_issued_drawings_for_user') {

    $user_id = isset($_REQUEST['user_id']) ? (int)$_REQUEST['user_id'] : 0;
    $status_filter = isset($_REQUEST['status_filter']) ? trim($_REQUEST['status_filter']) : 'All';

    // Validate user_id
    if ($user_id <= 0) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'User ID is required.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    $sql = "
        SELECT
            r.id,
            r.drawing_id AS no,
            r.revision AS rev,
            r.bag_name,
            r.ipd_catalog,
            r.status,
            CASE
                WHEN r.status = 'Rejected' THEN (SELECT DATE_FORMAT(h_rej.performed_at, '%d-%m-%Y %H:%i:%s')
                                                 FROM drawing_request_history h_rej
                                                 WHERE h_rej.request_id = r.id AND h_rej.event_type = 'rejected'
                                                 LIMIT 1)
                WHEN r.status = 'Pending' THEN NULL
                ELSE DATE_FORMAT(h_iss.performed_at, '%d-%m-%Y %H:%i:%s')
            END AS issue_reject_date,
            (SELECT CONCAT(u_ret.admin_name, ' at ', DATE_FORMAT(h_ret.performed_at, '%d-%m-%Y %H:%i:%s'))
             FROM drawing_request_history h_ret
             JOIN drawing_users u_ret ON h_ret.performed_by = u_ret.id
             WHERE h_ret.request_id = r.id AND h_ret.event_type = 'returned'
             LIMIT 1) AS returned_info,
            (SELECT CONCAT(u_rec.admin_name, ' at ', DATE_FORMAT(h_rec.performed_at, '%d-%m-%Y %H:%i:%s'))
             FROM drawing_request_history h_rec
             JOIN drawing_users u_rec ON h_rec.performed_by = u_rec.id
             WHERE h_rec.request_id = r.id AND h_rec.event_type = 'received'
             LIMIT 1) AS received_info,
            (SELECT CONCAT(u_rej.admin_name, ' at ', DATE_FORMAT(h_rej.performed_at, '%d-%m-%Y %H:%i:%s'))
             FROM drawing_request_history h_rej
             JOIN drawing_users u_rej ON h_rej.performed_by = u_rej.id
             WHERE h_rej.request_id = r.id AND h_rej.event_type = 'rejected'
             LIMIT 1) AS rejected_info,
            (SELECT remarks FROM drawing_request_history
             WHERE request_id = r.id AND event_type = 'rejected'
             LIMIT 1) AS remarks
        FROM drawing_requests r
        LEFT JOIN drawing_request_history h_iss ON r.id = h_iss.request_id AND h_iss.event_type = 'issued'
        WHERE r.requested_by = " . $user_id . "
        AND r.status IN ('Pending', 'Issued', 'Returned', 'Received', 'Rejected')
        AND (r.status = '" . $db->prepare_input($status_filter) . "' OR '" . $db->prepare_input($status_filter) . "' = 'All')
        ORDER BY r.id DESC
        LIMIT 500
    ";

    $result = $db->Execute($sql);

    $data = array();
    while ($result && !$result->EOF) {
        $row = $result->fields;
        $data[] = array(
            'id'                => (int)$row['id'],
            'no'                => $row['no'],
            'rev'               => $row['rev'],
            'bag_name'          => $row['bag_name'],
            'ipd_catalog'       => $row['ipd_catalog'],
            'status'            => $row['status'],
            'issue_reject_date' => $row['issue_reject_date'],
            'returned_info'     => $row['returned_info'],
            'received_info'     => $row['received_info'],
            'rejected_info'     => $row['rejected_info'],
            'remarks'           => $row['remarks'],
        );
        $result->MoveNext();
    }

    $OUTPUT['response'] = 'true';
    $OUTPUT['message']  = 'OK';
    $OUTPUT['total']    = count($data);
    $OUTPUT['data']     = $data;

// ------------------------------------------------
// ACTION: return_drawing_request
// Method: POST
// Params: request_id, user_id
// Returns: success/failure of return operation
// ------------------------------------------------
} elseif ($action === 'return_drawing_request') {

    $request_id = isset($_REQUEST['request_id']) ? (int)$_REQUEST['request_id'] : 0;
    $user_id = isset($_REQUEST['user_id']) ? (int)$_REQUEST['user_id'] : 0;

    // Validate inputs
    if ($request_id <= 0 || $user_id <= 0) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Request ID and user ID are required.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Check current status
    $status_check = $db->Execute("SELECT status, drawing_id FROM drawing_requests WHERE id = " . $request_id);
    if (!$status_check || $status_check->EOF) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Request not found.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    $current_status = $status_check->fields['status'];
    if ($current_status != 'Issued') {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Drawing has already been ' . strtolower($current_status) . '.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Update status to Returned
    $update_result = $db->Execute("UPDATE drawing_requests SET status = 'Returned' WHERE id = " . $request_id);

    if ($update_result) {
        // Log history
        $history_sql = "INSERT INTO drawing_request_history
                        (request_id, event_type, performed_by, revision)
                        VALUES (" . $request_id . ", 'returned', " . $user_id . ",
                               (SELECT revision FROM drawing_requests WHERE id = " . $request_id . "))";
        $db->Execute($history_sql);

        $OUTPUT['response'] = 'true';
        $OUTPUT['message']  = 'Drawing returned successfully.';
    } else {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Failed to update return status.';
    }

// ------------------------------------------------
// ACTION: get_returned_drawings
// Method: GET or POST
// Params: status_filter (optional) - filter by status ('All', 'Returned', 'Received')
// Returns: list of returned/received drawings for receiving
// ------------------------------------------------
} elseif ($action === 'get_returned_drawings') {

    $status_filter = isset($_REQUEST['status_filter']) ? trim($_REQUEST['status_filter']) : 'All';

    $sql = "
        SELECT 
            r.id,
            r.drawing_id AS no,
            r.revision AS rev,
            r.bag_name,
            r.ipd_catalog,
            r.status,
            u.admin_name AS returned_by,
            DATE_FORMAT(r.requested_at, '%d-%m-%Y %H:%i:%s') AS return_date,
            (SELECT CONCAT(u_rec.admin_name, ' at ', DATE_FORMAT(h_rec.performed_at, '%d-%m-%Y %H:%i:%s'))
             FROM drawing_request_history h_rec
             JOIN drawing_users u_rec ON h_rec.performed_by = u_rec.id
             WHERE h_rec.request_id = r.id AND h_rec.event_type = 'received'
             LIMIT 1) AS received_info
        FROM drawing_requests r
        JOIN drawing_users u ON r.requested_by = u.id
        WHERE r.status IN ('Returned', 'Received')
        AND (r.status = '" . $db->prepare_input($status_filter) . "' OR '" . $db->prepare_input($status_filter) . "' = 'All')
        ORDER BY r.requested_at DESC
        LIMIT 500
    ";

    $result = $db->Execute($sql);

    $data = array();
    while ($result && !$result->EOF) {
        $row = $result->fields;
        $data[] = array(
            'id'            => (int)$row['id'],
            'no'            => $row['no'],
            'rev'           => $row['rev'],
            'bag_name'      => $row['bag_name'],
            'ipd_catalog'   => $row['ipd_catalog'],
            'status'        => $row['status'],
            'returned_by'   => $row['returned_by'],
            'return_date'   => $row['return_date'],
            'received_info' => $row['received_info'],
        );
        $result->MoveNext();
    }

    $OUTPUT['response'] = 'true';
    $OUTPUT['message']  = 'OK';
    $OUTPUT['total']    = count($data);
    $OUTPUT['data']     = $data;

// ------------------------------------------------
// ACTION: receive_drawing_request
// Method: POST
// Params: request_id, user_id
// Returns: success/failure of receive operation
// ------------------------------------------------
} elseif ($action === 'receive_drawing_request') {

    $request_id = isset($_REQUEST['request_id']) ? (int)$_REQUEST['request_id'] : 0;
    $user_id = isset($_REQUEST['user_id']) ? (int)$_REQUEST['user_id'] : 0;

    // Validate inputs
    if ($request_id <= 0 || $user_id <= 0) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Request ID and user ID are required.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Check current status
    $status_check = $db->Execute("SELECT status FROM drawing_requests WHERE id = " . $request_id);
    if (!$status_check || $status_check->EOF) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Request not found.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    $current_status = $status_check->fields['status'];
    if ($current_status != 'Returned') {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Drawing has already been ' . strtolower($current_status) . '.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Log history BEFORE updating status
    $history_sql = "INSERT INTO drawing_request_history
                    (request_id, event_type, performed_by, revision)
                    VALUES (" . $request_id . ", 'received', " . $user_id . ",
                           (SELECT revision FROM drawing_requests WHERE id = " . $request_id . "))";
    $db->Execute($history_sql);

    // Update status to Received
    $update_result = $db->Execute("UPDATE drawing_requests SET status = 'Received' WHERE id = " . $request_id);

    if ($update_result) {
        $OUTPUT['response'] = 'true';
        $OUTPUT['message']  = 'Drawing received successfully.';
    } else {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Failed to update receive status.';
    }

// ------------------------------------------------
// ACTION: get_report_data
// Method: GET or POST
// Params: from_date (optional), to_date (optional), status_filter (optional)
// Returns: report data with full lifecycle information
// ------------------------------------------------
} elseif ($action === 'get_report_data') {

    $from_date = isset($_REQUEST['from_date']) ? trim($_REQUEST['from_date']) : '';
    $to_date = isset($_REQUEST['to_date']) ? trim($_REQUEST['to_date']) : '';
    $status_filter = isset($_REQUEST['status_filter']) ? trim($_REQUEST['status_filter']) : 'All';

    // Build filters
    $filters = array();
    if ($from_date && $to_date) {
        $filters[] = "DATE(h_req.performed_at) BETWEEN '" . $db->prepare_input($from_date) . "' AND '" . $db->prepare_input($to_date) . "'";
    }

    if ($status_filter === 'All') {
        $filters[] = "r.status IN ('Pending', 'open', 'Issued', 'Rejected', 'Returned', 'Received')";
    } elseif ($status_filter === 'Pending') {
        $filters[] = "r.status IN ('Pending', 'open')";
    } else {
        $filters[] = "r.status = '" . $db->prepare_input($status_filter) . "'";
    }

    $where_clause = count($filters) > 0 ? "WHERE " . implode(" AND ", $filters) : "";

    $sql = "
        SELECT 
            r.id,
            r.drawing_id AS no,
            h_req.revision AS req_rev,
            h_iss.revision AS iss_rev,
            r.status,
            r.bag_name,
            r.ipd_catalog,
            DATE_FORMAT(h_req.performed_at, '%d-%m-%Y %H:%i:%s') AS req_time,
            u_req.admin_name AS req_name,
            DATE_FORMAT(h_iss.performed_at, '%d-%m-%Y %H:%i:%s') AS iss_time,
            u_iss.admin_name AS iss_name,
            DATE_FORMAT(h_ret.performed_at, '%d-%m-%Y %H:%i:%s') AS ret_time,
            u_ret.admin_name AS ret_name,
            DATE_FORMAT(h_rec.performed_at, '%d-%m-%Y %H:%i:%s') AS rec_time,
            u_rec.admin_name AS rec_name,
            DATE_FORMAT(h_rej.performed_at, '%d-%m-%Y %H:%i:%s') AS rej_time,
            u_rej.admin_name AS rej_name,
            h_rej.remarks AS rej_remarks
        FROM drawing_requests r
        LEFT JOIN drawing_request_history h_req 
            ON h_req.id = (
                SELECT MAX(id) 
                FROM drawing_request_history 
                WHERE request_id = r.id 
                AND event_type = 'requested'
            )
        LEFT JOIN drawing_users u_req 
            ON h_req.performed_by = u_req.id
        LEFT JOIN drawing_request_history h_iss 
            ON h_iss.id = (
                SELECT MAX(id) 
                FROM drawing_request_history 
                WHERE request_id = r.id 
                AND event_type = 'issued'
            )
        LEFT JOIN drawing_users u_iss 
            ON h_iss.performed_by = u_iss.id
        LEFT JOIN drawing_request_history h_ret 
            ON h_ret.id = (
                SELECT MAX(id) 
                FROM drawing_request_history 
                WHERE request_id = r.id 
                AND event_type = 'returned'
            )
        LEFT JOIN drawing_users u_ret 
            ON h_ret.performed_by = u_ret.id
        LEFT JOIN drawing_request_history h_rec 
            ON h_rec.id = (
                SELECT MAX(id) 
                FROM drawing_request_history 
                WHERE request_id = r.id 
                AND event_type = 'received'
            )
        LEFT JOIN drawing_users u_rec 
            ON h_rec.performed_by = u_rec.id
        LEFT JOIN drawing_request_history h_rej 
            ON h_rej.id = (
                SELECT MAX(id) 
                FROM drawing_request_history 
                WHERE request_id = r.id 
                AND event_type = 'rejected'
            )
        LEFT JOIN drawing_users u_rej 
            ON h_rej.performed_by = u_rej.id
        " . $where_clause . "
        ORDER BY r.id DESC 
        LIMIT 1000
    ";

    $result = $db->Execute($sql);

    $data = array();
    while ($result && !$result->EOF) {
        $row = $result->fields;

        // Determine revision (issued revision if exists, else requested)
        $rev = isset($row['iss_rev']) && $row['iss_rev'] ? $row['iss_rev'] : ($row['req_rev'] ?: '');

        // Format time entries
        $req_info = ($row['req_name'] && $row['req_time']) ? $row['req_name'] . " at " . $row['req_time'] : "—";
        $iss_info = ($row['iss_name'] && $row['iss_time']) ? $row['iss_name'] . " at " . $row['iss_time'] : "—";
        $ret_info = ($row['ret_name'] && $row['ret_time']) ? $row['ret_name'] . " at " . $row['ret_time'] : "—";
        $rec_info = ($row['rec_name'] && $row['rec_time']) ? $row['rec_name'] . " at " . $row['rec_time'] : "—";
        $rej_info = ($row['rej_name'] && $row['rej_time']) ? $row['rej_name'] . " at " . $row['rej_time'] : "—";

        // Override iss_info if rejected
        if ($row['status'] === 'Rejected' && $row['rej_name'] && $row['rej_time']) {
            $iss_info = "REJECTED - " . $row['rej_name'] . " at " . $row['rej_time'];
        }

        $data[] = array(
            'id'           => (int)$row['id'],
            'no'           => $row['no'],
            'rev'          => $rev,
            'bag_name'     => $row['bag_name'] ?: '',
            'ipd_catalog'  => $row['ipd_catalog'] ?: '',
            'status'       => $row['status'],
            'remarks'      => $row['rej_remarks'] ?: '',
            'req_info'     => $req_info,
            'iss_info'     => $iss_info,
            'ret_info'     => $ret_info,
            'rec_info'     => $rec_info,
            'rej_info'     => $rej_info,
        );
        $result->MoveNext();
    }

    $OUTPUT['response'] = 'true';
    $OUTPUT['message']  = 'OK';
    $OUTPUT['total']    = count($data);
    $OUTPUT['data']     = $data;

// ------------------------------------------------
// ACTION: get_users
// Method: GET or POST
// Params: (none required)
// Returns: list of all users
// ------------------------------------------------
} elseif ($action === 'get_users') {

    $sql = "SELECT id, admin_name, department, access_tokens, user_role
            FROM drawing_users
            WHERE is_deleted = 0
            ORDER BY id";

    $result = $db->Execute($sql);

    $data = array();
    while ($result && !$result->EOF) {
        $row = $result->fields;

        // Parse access_tokens JSON
        $access_tokens = json_decode($row['access_tokens'], true);
        if (!is_array($access_tokens)) {
            $access_tokens = array();
        }

        // Parse user_role JSON
        $user_role = json_decode($row['user_role'], true);
        if (!is_array($user_role)) {
            $user_role = array();
        }

        $data[] = array(
            'id'            => (int)$row['id'],
            'admin_name'    => $row['admin_name'],
            'department'    => $row['department'],
            'access_tokens' => $access_tokens,
            'user_role'     => $user_role,
        );
        $result->MoveNext();
    }

    $OUTPUT['response'] = 'true';
    $OUTPUT['message']  = 'OK';
    $OUTPUT['total']    = count($data);
    $OUTPUT['data']     = $data;

// ------------------------------------------------
// ACTION: create_user
// Method: POST
// Params: username, password, department, access_tokens (JSON array)
// ------------------------------------------------
} elseif ($action === 'create_user') {

    $username = isset($_REQUEST['username']) ? trim($_REQUEST['username']) : '';
    $password = isset($_REQUEST['password']) ? trim($_REQUEST['password']) : '';
    $department = isset($_REQUEST['department']) ? trim($_REQUEST['department']) : '';
    $access_tokens_raw = isset($_REQUEST['access_tokens']) ? $_REQUEST['access_tokens'] : '[]';

    // Validate inputs
    if ($username === '' || $password === '' || $department === '') {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Username, password, and department are required.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Parse access_tokens
    $access_tokens = json_decode($access_tokens_raw, true);
    if (!is_array($access_tokens)) {
        $access_tokens = array();
    }

    // Check if username already exists
    $check_sql = "SELECT id FROM drawing_users WHERE admin_name = '" . $db->Escape($username) . "' AND is_deleted = 0";
    $check_result = $db->Execute($check_sql);
    if ($check_result && !$check_result->EOF) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Username already exists.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Hash password
    $password_md5 = md5($password);

    // Insert user
    $insert_sql = "INSERT INTO drawing_users (admin_name, admin_pass, department, access_tokens, user_role, is_deleted)
                   VALUES ('" . $db->Escape($username) . "', '" . $password_md5 . "', '" . $db->Escape($department) . "', '" . $db->Escape(json_encode($access_tokens)) . "', '[]', 0)";

    $insert_result = $db->Execute($insert_sql);

    if ($insert_result) {
        $user_id = $db->Insert_ID();
        $OUTPUT['response'] = 'true';
        $OUTPUT['message']  = 'User created successfully.';
        $OUTPUT['user_id']  = $user_id;
    } else {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Failed to create user.';
    }

// ------------------------------------------------
// ACTION: update_user
// Method: POST
// Params: user_id, username, password (optional), department, access_tokens (JSON array)
// ------------------------------------------------
} elseif ($action === 'update_user') {

    $user_id = isset($_REQUEST['user_id']) ? (int)$_REQUEST['user_id'] : 0;
    $username = isset($_REQUEST['username']) ? trim($_REQUEST['username']) : '';
    $password = isset($_REQUEST['password']) ? trim($_REQUEST['password']) : '';
    $department = isset($_REQUEST['department']) ? trim($_REQUEST['department']) : '';
    $access_tokens_raw = isset($_REQUEST['access_tokens']) ? $_REQUEST['access_tokens'] : '[]';

    // Validate inputs
    if ($user_id <= 0 || $username === '' || $department === '') {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'User ID, username, and department are required.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Parse access_tokens
    $access_tokens = json_decode($access_tokens_raw, true);
    if (!is_array($access_tokens)) {
        $access_tokens = array();
    }

    // Check if username already exists for another user
    $check_sql = "SELECT id FROM drawing_users WHERE admin_name = '" . $db->Escape($username) . "' AND id != " . $user_id . " AND is_deleted = 0";
    $check_result = $db->Execute($check_sql);
    if ($check_result && !$check_result->EOF) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Username already exists.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Build update query
    if ($password !== '') {
        $password_md5 = md5($password);
        $update_sql = "UPDATE drawing_users SET admin_name = '" . $db->Escape($username) . "', admin_pass = '" . $password_md5 . "', department = '" . $db->Escape($department) . "', access_tokens = '" . $db->Escape(json_encode($access_tokens)) . "' WHERE id = " . $user_id;
    } else {
        $update_sql = "UPDATE drawing_users SET admin_name = '" . $db->Escape($username) . "', department = '" . $db->Escape($department) . "', access_tokens = '" . $db->Escape(json_encode($access_tokens)) . "' WHERE id = " . $user_id;
    }

    $update_result = $db->Execute($update_sql);

    if ($update_result) {
        $OUTPUT['response'] = 'true';
        $OUTPUT['message']  = 'User updated successfully.';
    } else {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Failed to update user.';
    }

// ------------------------------------------------
// ACTION: delete_user
// Method: POST
// Params: user_id
// ------------------------------------------------
} elseif ($action === 'delete_user') {

    $user_id = isset($_REQUEST['user_id']) ? (int)$_REQUEST['user_id'] : 0;

    // Validate input
    if ($user_id <= 0) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'User ID is required.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Soft delete user
    $delete_sql = "UPDATE drawing_users SET is_deleted = 1 WHERE id = " . $user_id;
    $delete_result = $db->Execute($delete_sql);

    if ($delete_result) {
        $OUTPUT['response'] = 'true';
        $OUTPUT['message']  = 'User deleted successfully.';
    } else {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Failed to delete user.';
    }

// ------------------------------------------------
// ACTION: assign_user_role
// Method: POST
// Params: user_id, user_role (JSON array)
// ------------------------------------------------
} elseif ($action === 'assign_user_role') {

    $user_id = isset($_REQUEST['user_id']) ? (int)$_REQUEST['user_id'] : 0;
    $user_role_raw = isset($_REQUEST['user_role']) ? $_REQUEST['user_role'] : '[]';

    // Validate input
    if ($user_id <= 0) {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'User ID is required.';
        header('Content-Type: application/json');
        echo json_encode($OUTPUT);
        exit;
    }

    // Parse user_role
    $user_role = json_decode($user_role_raw, true);
    if (!is_array($user_role)) {
        $user_role = array();
    }

    // Define role permissions
    $role_permissions = array(
        'ADMIN'     => array(1, 2, 3, 4, 5, 6),
        'ISSUER'    => array(2, 4, 5),
        'REQUESTER' => array(1, 3, 5),
    );

    // Merge permissions from selected roles
    $merged_tokens = array();
    foreach ($user_role as $role) {
        if (isset($role_permissions[$role])) {
            $merged_tokens = array_merge($merged_tokens, $role_permissions[$role]);
        }
    }
    $merged_tokens = array_unique($merged_tokens);
    sort($merged_tokens);

    // Update user
    $update_sql = "UPDATE drawing_users SET user_role = '" . $db->Escape(json_encode($user_role)) . "', access_tokens = '" . $db->Escape(json_encode($merged_tokens)) . "' WHERE id = " . $user_id;
    $update_result = $db->Execute($update_sql);

    if ($update_result) {
        $OUTPUT['response'] = 'true';
        $OUTPUT['message']  = 'User role assigned successfully.';
        $OUTPUT['permissions'] = $merged_tokens;
    } else {
        $OUTPUT['response'] = 'false';
        $OUTPUT['message']  = 'Failed to assign user role.';
    }

// ------------------------------------------------
// ACTION: get_departments
// Method: GET or POST
// Params: (none required)
// Returns: list of departments
// ------------------------------------------------
} elseif ($action === 'get_departments') {

    $sql = "SELECT description_short FROM departments ORDER BY description_short";
    $result = $db->Execute($sql);

    $data = array();
    while ($result && !$result->EOF) {
        $row = $result->fields;
        if ($row['description_short']) {
            $data[] = $row['description_short'];
        }
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
    $OUTPUT['message']  = 'Unknown or missing action: ' . htmlspecialchars($action);
    $OUTPUT['data']     = array();

}

header('Content-Type: application/json');
echo json_encode($OUTPUT);
?>
