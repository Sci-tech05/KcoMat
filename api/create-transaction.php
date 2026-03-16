<?php
/**
 * Bridge PHP pour créer une transaction FedaPay via SDK officielle.
 * Entrée: JSON sur STDIN
 * Sortie: JSON sur STDOUT
 */

error_reporting(E_ALL & ~E_DEPRECATED);
ini_set('display_errors', '0');

$sdk_candidates = [
    __DIR__ . '/../vendor/autoload.php',
    dirname(__DIR__) . '/vendor/autoload.php',
    'vendor/autoload.php',
];

$sdk_path = null;
foreach ($sdk_candidates as $candidate) {
    if (file_exists($candidate)) {
        $sdk_path = $candidate;
        break;
    }
}

if (!$sdk_path) {
    exit(json_encode([
        'success' => false,
        'error' => 'SDK FedaPay non trouvée. Chemins essayés: ' . implode(', ', $sdk_candidates),
        'transaction_id' => null,
    ]));
}

require_once $sdk_path;

use FedaPay\FedaPay;
use FedaPay\Transaction;

try {
    $input_raw = file_get_contents('php://stdin');
    $input = json_decode($input_raw, true);

    if (!$input) {
        throw new Exception('Données JSON invalides');
    }

    $api_key = $input['api_key'] ?? '';
    $environment = $input['environment'] ?? 'sandbox';

    if (!$api_key) {
        throw new Exception('Clé API FedaPay manquante');
    }

    FedaPay::setApiKey($api_key);
    FedaPay::setEnvironment($environment);
    FedaPay::setVerifySslCerts(false);

    $required = ['amount', 'description', 'currency', 'country', 'callback_url'];
    foreach ($required as $field) {
        if (empty($input[$field])) {
            throw new Exception("Champ requis manquant: $field");
        }
    }

    $transaction_data = [
        'amount' => (int)$input['amount'],
        'description' => $input['description'],
        'currency' => ['iso' => $input['currency']],
        'callback_url' => $input['callback_url'],
    ];

    if (!empty($input['customer'])) {
        $customer = $input['customer'];
        $transaction_data['customer'] = [
            'firstname' => $customer['firstname'] ?? '',
            'lastname' => $customer['lastname'] ?? '',
            'email' => $customer['email'] ?? '',
            'phone_number' => [
                'number' => $customer['phone'] ?? '',
                'country' => $input['country'],
            ],
        ];
    }

    if (!empty($input['metadata'])) {
        $transaction_data['custom_metadata'] = $input['metadata'];
    }

    $transaction = Transaction::create($transaction_data);

    if (!$transaction || !isset($transaction->id)) {
        throw new Exception('Impossible de créer la transaction FedaPay');
    }

    $token_data = $transaction->generateToken();

    if (!$token_data) {
        throw new Exception('Impossible de générer le token de paiement');
    }

    // Le SDK peut renvoyer soit une string JWT, soit une structure {token, url}.
    $token = null;
    $process_url = null;

    if (is_string($token_data)) {
        $token = $token_data;
    } elseif (is_array($token_data)) {
        $token = $token_data['token'] ?? null;
        $process_url = $token_data['url'] ?? null;
    } elseif (is_object($token_data)) {
        if (isset($token_data->token)) {
            $token = $token_data->token;
        }
        if (isset($token_data->url)) {
            $process_url = $token_data->url;
        }
    }

    if (!$token || !is_string($token)) {
        throw new Exception('Token FedaPay invalide: format non reconnu');
    }

    $fallback_checkout_url = ($environment === 'sandbox'
        ? 'https://sandbox-checkout.fedapay.com/checkout/'
        : 'https://checkout.fedapay.com/checkout/') . $token;

    $checkout_url = $process_url ?: $fallback_checkout_url;

    exit(json_encode([
        'success' => true,
        'transaction_id' => $transaction->id,
        'token' => $token,
        'checkout_url' => $checkout_url,
        'process_url' => $process_url,
        'amount' => $transaction->amount,
        'currency' => $transaction->currency->iso ?? 'XOF',
    ]));

} catch (Exception $e) {
    exit(json_encode([
        'success' => false,
        'error' => $e->getMessage(),
        'error_file' => $e->getFile(),
        'error_line' => $e->getLine(),
        'transaction_id' => null,
    ]));
}
