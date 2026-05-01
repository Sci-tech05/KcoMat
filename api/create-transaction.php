<?php
/**
 * Bridge PHP FedaPay - Version corrigée avec logs détaillés
 */

error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');

function fedapay_log($message, $level = 'INFO') {
    $log_file = __DIR__ . '/fedapay_bridge.log';
    $timestamp = date('Y-m-d H:i:s');
    file_put_contents($log_file, "[$timestamp] [$level] $message\n", FILE_APPEND | LOCK_EX);
}

fedapay_log("=== NOUVELLE TENTATIVE DE PAIEMENT ===");

$sdk_candidates = [
    __DIR__ . '/../vendor/autoload.php',
    dirname(__DIR__) . '/vendor/autoload.php',
    __DIR__ . '/vendor/autoload.php',
    dirname(__DIR__, 2) . '/vendor/autoload.php',
    '/home/KcoMat0/KcoMat/vendor/autoload.php',           // Chemin typique PythonAnywhere
    '/home/kcomat0/.local/share/virtualenvs/.../vendor/autoload.php' // au cas où
];

$sdk_path = null;
foreach ($sdk_candidates as $candidate) {
    if (file_exists($candidate)) {
        $sdk_path = $candidate;
        fedapay_log("SDK trouvé : " . $sdk_path);
        break;
    }
}

if (!$sdk_path) {
    fedapay_log("SDK NON TROUVÉ ! Chemins essayés : " . implode(" | ", $sdk_candidates), 'ERROR');
    exit(json_encode([
        'success' => false,
        'error' => 'SDK FedaPay non trouvé. Vérifiez le dossier vendor/',
        'transaction_id' => null,
    ]));
}

require_once $sdk_path;
fedapay_log("SDK chargé avec succès");

use FedaPay\FedaPay;
use FedaPay\Transaction;

try {
    $input_raw = file_get_contents('php://stdin');
    $input = json_decode($input_raw, true);

    if (!$input) {
        throw new Exception('JSON invalide');
    }

    $api_key = $input['api_key'] ?? '';
    $environment = strtolower($input['environment'] ?? 'sandbox');

    fedapay_log("Environment : " . $environment);
    fedapay_log("API Key début : " . substr($api_key, 0, 25) . "...");

    if (empty($api_key)) {
        throw new Exception('Clé API manquante');
    }

    FedaPay::setApiKey($api_key);
    FedaPay::setEnvironment($environment);
    FedaPay::setVerifySslCerts($environment === 'live');

    fedapay_log("SSL Verify : " . ($environment === 'live' ? 'true' : 'false'));

    // Champs requis
    $required = ['amount', 'description', 'currency', 'country', 'callback_url'];
    foreach ($required as $field) {
        if (empty($input[$field])) {
            throw new Exception("Champ manquant : $field");
        }
    }

    $transaction_data = [
        'amount'       => (int)$input['amount'],
        'description'  => $input['description'],
        'currency'     => ['iso' => strtoupper($input['currency'])],
        'callback_url' => $input['callback_url'],
    ];

    if (!empty($input['customer'])) {
        $c = $input['customer'];
        $transaction_data['customer'] = [
            'firstname' => $c['firstname'] ?? '',
            'lastname'  => $c['lastname'] ?? '',
            'email'     => $c['email'] ?? '',
            'phone_number' => [
                'number'  => $c['phone'] ?? '',
                'country' => strtoupper($input['country']),
            ],
        ];
    }

    if (!empty($input['metadata'])) {
        $transaction_data['custom_metadata'] = $input['metadata'];
    }

    fedapay_log("Appel à Transaction::create()...");

    $transaction = Transaction::create($transaction_data);

    if (!$transaction || empty($transaction->id)) {
        throw new Exception('Transaction non créée (pas de ID)');
    }

    fedapay_log("Transaction créée - ID: " . $transaction->id);

    $token_data = $transaction->generateToken();

    // Extraction token
    $token = null;
    $process_url = null;

    if (is_string($token_data)) $token = $token_data;
    elseif (is_array($token_data)) {
        $token = $token_data['token'] ?? $token_data['jwt'] ?? null;
        $process_url = $token_data['url'] ?? null;
    } elseif (is_object($token_data)) {
        $token = $token_data->token ?? null;
        $process_url = $token_data->url ?? null;
    }

    if (!$token) {
        throw new Exception('Impossible de générer le token');
    }

    $checkout_url = $process_url ?: 
        ($environment === 'live' 
            ? 'https://live-checkout.fedapay.com/checkout/' 
            : 'https://checkout.fedapay.com/checkout/') . $token;

    fedapay_log("Succès - Checkout URL générée");

    exit(json_encode([
        'success'        => true,
        'transaction_id' => $transaction->id,
        'token'          => $token,
        'checkout_url'   => $checkout_url,
        'amount'         => $transaction->amount ?? $input['amount'],
        'currency'       => 'XOF',
    ]));

} catch (Exception $e) {
    fedapay_log("ERREUR : " . $e->getMessage() . " | Ligne " . $e->getLine(), 'ERROR');
    exit(json_encode([
        'success' => false,
        'error'   => $e->getMessage(),
        'error_line' => $e->getLine(),
    ]));
}