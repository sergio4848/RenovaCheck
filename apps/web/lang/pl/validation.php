<?php

// Rules not listed here fall back to lang/en/validation.php (fallback locale).
return [
    'accepted' => 'Pole :attribute musi zostać zaakceptowane.',
    'array' => 'Pole :attribute musi być tablicą.',
    'boolean' => 'Pole :attribute musi mieć wartość prawda albo fałsz.',
    'date' => 'Pole :attribute nie jest prawidłową datą.',
    'email' => 'Pole :attribute musi być prawidłowym adresem e-mail.',
    'exists' => 'Wybrana wartość pola :attribute jest nieprawidłowa.',
    'file' => 'Pole :attribute musi być plikiem.',
    'in' => 'Wybrana wartość pola :attribute jest nieprawidłowa.',
    'integer' => 'Pole :attribute musi być liczbą całkowitą.',
    'max' => [
        'array' => 'Pole :attribute może zawierać maksymalnie :max elementów.',
        'file' => 'Plik :attribute może mieć maksymalnie :max kB.',
        'numeric' => 'Pole :attribute nie może być większe niż :max.',
        'string' => 'Pole :attribute może mieć maksymalnie :max znaków.',
    ],
    'mimes' => 'Pole :attribute musi być plikiem typu: :values.',
    'min' => [
        'array' => 'Pole :attribute musi zawierać co najmniej :min elementów.',
        'file' => 'Plik :attribute musi mieć co najmniej :min kB.',
        'numeric' => 'Pole :attribute musi być nie mniejsze niż :min.',
        'string' => 'Pole :attribute musi mieć co najmniej :min znaków.',
    ],
    'numeric' => 'Pole :attribute musi być liczbą.',
    'regex' => 'Format pola :attribute jest nieprawidłowy.',
    'required' => 'Pole :attribute jest wymagane.',
    'string' => 'Pole :attribute musi być tekstem.',
    'unique' => 'Taka wartość pola :attribute już istnieje.',
    'uuid' => 'Pole :attribute musi być prawidłowym identyfikatorem UUID.',

    'custom' => [],
    'attributes' => [
        'email' => 'e-mail',
        'password' => 'hasło',
    ],
];
