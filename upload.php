<?php
// upload.php
// Recebe upload via multipart/form-data (campo "file")
// Salva em uploads/ com timestamp e retorna JSON.

header('Content-Type: application/json');

// Configurações
$uploadDir = __DIR__ . '/uploads/';
if (!is_dir($uploadDir)) {
    mkdir($uploadDir, 0755, true);
}

// (Opcional) Verificar token de autorização via header
$expectedToken = null; // se usar, coloque aqui
if ($expectedToken !== null) {
    $headers = getallheaders();
    if (!isset($headers['Authorization'])) {
        http_response_code(401);
        echo json_encode(['error' => 'Authorization header missing']);
        exit;
    }
    $auth = $headers['Authorization'];
    if (strpos($auth, 'Bearer ') === 0) {
        $token = substr($auth, 7);
    } else {
        $token = $auth;
    }
    if ($token !== $expectedToken) {
        http_response_code(403);
        echo json_encode(['error' => 'Invalid token']);
        exit;
    }
}

// Checar se arquivo foi enviado
if (!isset($_FILES['file'])) {
    http_response_code(400);
    echo json_encode(['error' => 'No file uploaded (field "file" missing)']);
    exit;
}

$file = $_FILES['file'];

if ($file['error'] !== UPLOAD_ERR_OK) {
    http_response_code(500);
    echo json_encode(['error' => 'Upload error code: ' . $file['error']]);
    exit;
}

// Segurança básica: limitar tipos/size (opcional)
$maxBytes = 5 * 1024 * 1024; // 5 MB, ajuste conforme necessário
if ($file['size'] > $maxBytes) {
    http_response_code(413);
    echo json_encode(['error' => 'File too large']);
    exit;
}

// Nome seguro
$origName = basename($file['name']);
$time = date('Ymd_His');
$saveName = $time . "_" . preg_replace('/[^A-Za-z0-9._-]/', '_', $origName);
$destination = $uploadDir . $saveName;

if (!move_uploaded_file($file['tmp_name'], $destination)) {
    http_response_code(500);
    echo json_encode(['error' => 'Failed to move uploaded file']);
    exit;
}

// Registrar metadados (opcional)
$meta = [
    'saved_as' => $saveName,
    'original_name' => $origName,
    'size_bytes' => $file['size'],
    'uploaded_at' => date('c'),
    'uploader_ip' => $_SERVER['REMOTE_ADDR'] ?? null
];
file_put_contents($uploadDir . $saveName . '.meta.json', json_encode($meta, JSON_PRETTY_PRINT));

// Sucesso
http_response_code(200);
echo json_encode(['ok' => true, 'file' => $saveName]);
exit;
