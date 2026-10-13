<?php

namespace App\Enums;

/** Document types; values match packages/rules/doc_types.yaml and the synthetic ground truth. */
enum DocType: string
{
    case WniosekEkstrakt = 'wniosek_ekstrakt';
    case Oferta = 'oferta';
    case Umowa = 'umowa';
    case Aneks = 'aneks';
    case Faktura = 'faktura';
    case FakturaZaliczkowa = 'faktura_zaliczkowa';
    case FakturaKorygujaca = 'faktura_korygujaca';
    case ProtokolOdbioru = 'protokol_odbioru';
    case KartaProduktu = 'karta_produktu';

    public function label(): string
    {
        return __('doc_type.'.$this->value);
    }
}
