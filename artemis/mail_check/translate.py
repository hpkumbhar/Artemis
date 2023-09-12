import copy
import re
from enum import Enum
from typing import Callable, List, Optional, Tuple

from .scan import DKIMScanResult, DomainScanResult, ScanResult


class Language(Enum):
    en_US = "en_US"
    pl_PL = "pl_PL"


PLACEHOLDER = "__PLACEHOLDER__"


TRANSLATIONS = {
    Language.pl_PL: [
        (
            "SPF '~all' or '-all' directive not found. We recommend adding it, as it describes "
            "what should happen with messages that fail SPF verification. For example, "
            "'-all' will tell the recipient server to drop such messages.",
            "Nie znaleziono dyrektywy '~all' lub '-all' w rekordzie SPF. Rekomendujemy jej dodanie, ponieważ "
            "opisuje ona, jak powinny zostać potraktowane wiadomości, które zostaną odrzucone "
            "przez mechanizm SPF. Na przykład, dyrektywa '-all' wskazuje serwerowi odbiorcy, "
            "że powinien odrzucać takie wiadomości.",
        ),
        (
            "Valid SPF record not found. We recommend using all three mechanisms: SPF, DKIM and DMARC "
            "to decrease the possibility of successful e-mail message spoofing.",
            "Nie znaleziono poprawnego rekordu SPF. Rekomendujemy używanie wszystkich trzech mechanizmów: "
            "SPF, DKIM i DMARC, aby zmniejszyć szansę, że sfałszowana wiadomość zostanie zaakceptowana "
            "przez serwer odbiorcy.",
        ),
        (
            "Multiple SPF records found. We recommend leaving only one, as multiple SPF records "
            "can cause problems with some SPF implementations.",
            "Wykryto więcej niż jeden rekord SPF. Rekomendujemy pozostawienie jednego z nich - "
            "obecność wielu rekordów może powodować problemy w działaniu niektórych implementacji mechanizmu SPF.",
        ),
        (
            "The SPF record references a domain that doesn't have an SPF record. When using directives such "
            "as 'include' or 'redirect', remember, that the destination domain should have a proper SPF record.",
            "Rekord SPF odwołuje się do domeny, która nie zawiera rekordu SPF. W przypadku odwoływania się do "
            "innych domen za pomocą dyrektyw SPF takich jak 'include' lub 'redirect', domena docelowa powinna również "
            "zawierać rekord SPF.",
        ),
        (
            "SPF record causes too many void DNS lookups. Some implementations may require the number of "
            "failed DNS lookups (e.g. ones that reference a nonexistent domain) to be low. The DNS lookups "
            "are caused by directives such as 'mx' or 'include'.",
            "Rekord SPF powoduje zbyt wiele nieudanych zapytań DNS. Niektóre implementacje mechanizmu "
            "SPF wymagają, aby liczba nieudanych zapytań DNS (np. odwołujących się do nieistniejących domen) była "
            "niska. Takie zapytania DNS mogą być spowodowane np. przez dyrektywy SPF 'mx' czy 'include'.",
        ),
        (
            "SPF record includes an endless loop. Please check whether 'include' or 'redirect' directives don't "
            "create a loop where a domain redirects back to itself or earlier domain.",
            "Rekord SPF zawiera nieskończoną pętlę. Prosimy sprawdzić, czy dyrektywy SPF 'include' lub 'redirect' "
            "nie odwołują się z powrotem do tej samej domeny lub do wcześniejszych domen.",
        ),
        (
            "SPF record is not syntactically correct. Please closely inspect its syntax.",
            "Rekord SPF nie ma poprawnej składni. Prosimy o jego dokładną weryfikację.",
        ),
        (
            "SPF record causes too many DNS lookups. The DNS lookups are caused by directives such as 'mx' or 'include'. "
            "The specification requires the number of DNS lookups to be lower or equal to 10 to decrease load on DNS servers.",
            "Rekord SPF powoduje zbyt wiele zapytań DNS. Zapytania DNS są powodowane przez niektóre dyrektywy SPF, takie jak "
            "'mx' czy 'include'. Spefycikacja wymaga, aby liczba zapytań DNS nie przekraczała 10, aby nie powodować nadmiernego "
            "obciążenia serwerów DNS.",
        ),
        (
            "The ptr mechanism should not be used - https://tools.ietf.org/html/rfc7208#section-5.5",
            "Zgodnie ze specyfikacją SPF, nie należy używać mechanizmu 'ptr'. Pod adresem "
            "https://tools.ietf.org/html/rfc7208#section-5.5 można znaleźć uzasadnienie tej rekomendacji.",
        ),
        (
            "Valid DMARC record not found. We recommend using all three mechanisms: SPF, DKIM and DMARC "
            "to decrease the possibility of successful e-mail message spoofing.",
            "Nie znaleziono poprawnego rekordu DMARC. Rekomendujemy używanie wszystkich trzech mechanizmów: "
            "SPF, DKIM i DMARC, aby zmniejszyć szansę, żę sfałszowana wiadomość zostanie zaakceptowana "
            "przez serwer odbiorcy.",
        ),
        (
            "DMARC policy is 'none' and 'rua' is not set, which means that the DMARC setting is not effective.",
            "Polityka DMARC jest ustawiona na 'none' i nie ustawiono odbiorcy raportów w polu 'rua', co "
            "oznacza, że ustawienie DMARC nie będzie skuteczne.",
        ),
        (
            f"The DMARC record must be located at {PLACEHOLDER}, not {PLACEHOLDER}",
            f"Rekord DMARC powinien znajdować się w domenie {PLACEHOLDER}, nie {PLACEHOLDER}.",
        ),
        (
            "There are multiple DMARC records. We recommend leaving only one, as multiple "
            "DMARC records can cause problems with some DMARC implementations.",
            "Wykryto więcej niż jeden rekord DMARC. Rekomendujemy pozostawienie jednego z nich - "
            "obecność wielu rekordów może powodować problemy w działaniu niektórych implementacji "
            "mechanizmu DMARC.",
        ),
        (
            "There is a SPF record instead of DMARC one on the '_dmarc' subdomain.",
            "Zamiast rekordu DMARC wykryto rekord SPF w subdomenie '_dmarc'.",
        ),
        (
            "DMARC record is not syntactically correct. Please closely inspect its syntax.",
            "Rekord DMARC nie ma poprawnej składni. Prosimy o jego dokładną weryfikację.",
        ),
        (
            "DMARC record uses an invalid tag. Please refer to https://datatracker.ietf.org/doc/html/rfc7489#section-6.3 "
            "for the list of available tags.",
            "Rekord DMARC zawiera niepoprawne pole. Pod adresem "
            "https://cert.pl/posts/2021/10/mechanizmy-weryfikacji-nadawcy-wiadomosci/#dmarc-pola "
            "znajdziesz opis przykładowych pól, które mogą znaleźć się w takim rekordzie, a w specyfikacji mechanizmu "
            "DMARC pod adresem https://datatracker.ietf.org/doc/html/rfc7489#section-6.3 - opis wszystkich pól.",
        ),
        (
            "DMARC report URI is invalid. The report URI should be an e-mail address prefixed with mailto:.",
            "Adres raportów DMARC jest niepoprawny. Powinien to być adres e-mail rozpoczynający się od mailto:.",
        ),
        (
            "The destination of a DMARC report URI does not indicate that it accepts reports for the domain.",
            "Adres raportów DMARC nie wskazuje, że przyjmuje raporty z tej domeny.",
        ),
        (
            "Subdomain policy (sp=) should be reject for parked domains",
            "Polityka subdomen (sp=) powinna być ustawiona na 'reject' dla domen "
            "niesłużących do wysyłki poczty - serwer odbiorcy powinien odrzucać wiadomości z takich domen.",
        ),
        (
            "Policy (p=) should be reject for parked domains",
            "Polityka (p=) powinna być ustawiona na 'reject' dla domen niesłużących "
            "do wysyłki poczty - serwer odbiorcy powinien odrzucać wiadomości z takich domen.",
        ),
        (
            "Unrelated TXT record found in the '_dmarc' subdomain. We recommend removing it, as such unrelated "
            "records may cause problems with some DMARC implementations.",
            "Znaleziono niepowiązane rekordy TXT w subdomenie '_dmarc'. Rekomendujemy ich usunięcie, ponieważ "
            "niektóre serwery mogą w takiej sytuacji odrzucić konfigurację DMARC jako błędną.",
        ),
        (
            "The domain of the email address in a DMARC report URI is missing MX records. That means, that this domain "
            "may not receive DMARC reports.",
            "Domena adresu e-mail w adresie raportów DMARC nie zawiera rekordów MX. Oznacza to, że raporty DMARC mogą nie być "
            "poprawnie dostarczane.",
        ),
        (
            "DMARC policy is 'none', which means that besides reporting no action will be taken. The policy describes what "
            "action the recipient server should take when noticing a message that doesn't pass the verification. 'quarantine' policy "
            "suggests the recipient server to flag the message as spam and 'reject' policy suggests the recipient "
            "server to reject the message. We recommend using the 'quarantine' or 'reject' policy.",
            "Polityka DMARC jest ustawiona na 'none', co oznacza, że oprócz raportowania, żadna dodatkowa akcja nie zostanie "
            "wykonana. Polityka DMARC opisuje serwerowi odbiorcy, jaką akcję powinien podjąć, gdy wiadomość nie zostanie "
            "poprawnie zweryfikowana. Polityka 'quarantine' oznacza, że taka wiadomość powinna zostać oznaczona jako spam, a polityka 'reject' - że "
            "powinna zostać odrzucona przez serwer odbiorcy. Rekomendujemy korzystanie z polityki 'quarantine' lub 'reject'.",
        ),
        (
            "rua tag (destination for aggregate reports) not found",
            "Nie znaleziono tagu 'rua' (odbiorca zagregowanych raportów).",
        ),
        (
            "Whitespace in domain name detected. Please provide a correct domain name.",
            "Wykryto białe znaki w nazwie domeny. Prosimy o podanie poprawnej nazwy domeny.",
        ),
        (
            f"Unexpected character in domain detected: {PLACEHOLDER}. Please provide a correct domain name.",
            f"Wykryto błędne znaki w nazwie domeny: {PLACEHOLDER}. Prosimy o podanie poprawnej nazwy domeny.",
        ),
        (
            "Any text after the all mechanism is ignored",
            "Tekst umieszczony po dyrektywie 'all' zostanie zignorowany. Rekomendujemy jego usunięcie, lub, "
            "jeśli jest niezbędnym elementem konfiguracji, umieszczenie przed dyrektywą 'all' rekordu SPF.",
        ),
        (
            "No DKIM signature found",
            "Nie znaleziono podpisu DKIM. Rekomendujemy używanie wszystkich trzech mechanizmów: SPF, DKIM i DMARC, aby "
            "zmniejszyć szansę, żę sfałszowana wiadomość zostanie zaakceptowana przez serwer odbiorcy.",
        ),
        (
            "Found an invalid DKIM signature",
            "Znaleziono niepoprawny podpis mechanizmu DKIM.",
        ),
        (
            "SPF records containing macros aren't supported yet.",
            "Rekordy SPF zawierające makra nie są wspierane.",
        ),
        (
            f"The resolution lifetime expired after {PLACEHOLDER}",
            "Przekroczono czas oczekiwania na odpowiedź serwera DNS. Prosimy spróbować jeszcze raz.",
        ),
        (
            f"DMARC record at root of {PLACEHOLDER} has no effect",
            f"Rekord DMARC w domenie '{PLACEHOLDER}' (zamiast w subdomenie '_dmarc') nie zostanie uwzględniony.",
        ),
        (
            "Found a DMARC record that starts with whitespace. Please remove the whitespace, as some "
            "implementations may not process it correctly.",
            "Wykryto rekord DMARC zaczynający się od spacji lub innych białych znaków. Rekomendujemy ich "
            "usunięcie, ponieważ niektóre serwery pocztowe mogą nie zinterpretować takiego rekordu poprawnie.",
        ),
        (
            f"{PLACEHOLDER} does not have any MX records",
            f"Rekord SPF w domenie {PLACEHOLDER} korzysta z dyrektywy SPF 'mx', lecz nie wykryto rekordów MX, w związku "
            "z czym ta dyrektywa nie zadziała poprawnie.",
        ),
        (
            f"{PLACEHOLDER} does not have any A/AAAA records",
            f"Rekord SPF w domenie {PLACEHOLDER} korzysta z dyrektywy SPF 'a', lecz nie wykryto rekordów A/AAAA, w związku "
            "z czym ta dyrektywa nie zadziała poprawnie.",
        ),
        (
            f"{PLACEHOLDER} does not indicate that it accepts DMARC reports about {PLACEHOLDER} - Authorization record not found: {PLACEHOLDER}",
            f"Domena {PLACEHOLDER} nie wskazuje, że przyjmuje raporty DMARC na temat domeny {PLACEHOLDER} - nie wykryto rekordu autoryzacyjnego.",
        ),
        (
            "SPF type DNS records found. Use of DNS Type SPF has been removed in the standards track version of SPF, RFC 7208. These records "
            f"should be removed and replaced with TXT records: {PLACEHOLDER}",
            "Wykryto rekordy DNS o typie SPF. Wykorzystanie rekordów tego typu zostało usunięte ze standardu - powinny zostać zastąpione rekordami TXT.",
        ),
        (
            "Requested to scan a domain that is a public suffix, i.e. a domain such as .com where anybody could "
            "register their subdomain. Such domain don't have to have properly configured e-mail sender verification "
            "mechanisms. Please make sure you really wanted to check such domain and not its subdomain.",
            "Sprawdzają Państwo domenę z listy Public Suffix List (https://publicsuffix.org/) czyli taką jak .pl, gdzie  "
            "różne podmioty mogą zarejestrować swoje subdomeny. Takie domeny nie muszą mieć skonfigurowanych mechanizmów "
            "weryfikacji nadawcy poczty - konfigurowane są one w subdomenach. Prosimy o weryfikację nazwy sprawdzanej domeny.",
        ),
        (
            "Requested to scan a top-level domain. Top-level domains don't have to have properly configured e-mail sender "
            "verification mechanisms. Please make sure you really wanted to check such domain and not its subdomain."
            "Besides, the domain is not known to the Public Suffix List (https://publicsuffix.org/) - please verify whether "
            "it is correct.",
            "Sprawdzają Państwo domenę najwyższego poziomu. Domeny najwyższego poziomu nie muszą mieć "
            "skonfigurowanych mechanizmów weryfikacji nadawcy poczty - konfigurowane są one w subdomenach. Prosimy "
            "o weryfikację nazwy sprawdzanej domeny. Domena nie występuje również na Public Suffix List "
            "(https://publicsuffix.org/) - prosimy o weryfikację jej poprawności.",
        ),
        (
            "Please provide a correct domain name.",
            "Proszę podać poprawną nazwę domeny.",
        ),
        (
            f"Failed to retrieve MX records for the domain of {PLACEHOLDER} email address {PLACEHOLDER} - All nameservers failed to answer the query {PLACEHOLDER}",
            f"Nie udało się odczytać rekordów MX domeny adresu e-mail w dyrektywie {PLACEHOLDER}: {PLACEHOLDER} - serwery nazw nie odpowiedziały poprawnie na zapytanie.",
        ),
        (
            f"All nameservers failed to answer the query {PLACEHOLDER}. IN {PLACEHOLDER}",
            f"Żaden z przypisanych serwerów nazw domen nie odpowiedział na zapytanie dotyczące domeny {PLACEHOLDER}.",
        ),
        # Legacy messages translations - these will be used if some existing task result reside in the database
        # from previous runs, when an older version of this module was used.
        (
            "Valid DMARC record not found",
            "Nie znaleziono poprawnego rekordu DMARC. Rekomendujemy używanie wszystkich trzech mechanizmów: "
            "SPF, DKIM i DMARC, aby zmniejszyć szansę, żę sfałszowana wiadomość zostanie zaakceptowana "
            "przez serwer odbiorcy.",
        ),
        (
            "SPF ~all or -all directive not found",
            "Nie znaleziono dyrektywy '~all' lub '-all' w rekordzie SPF. Rekomendujemy jej dodanie, ponieważ "
            "opisuje ona, jak powinny zostać potraktowane wiadomości, które zostaną odrzucone "
            "przez mechanizm SPF. Na przykład, dyrektywa '-all' wskazuje serwerowi odbiorcy, "
            "że powinien odrzucać takie wiadomości.",
        ),
        (
            "DMARC policy is none and rua is not set, which means that the DMARC setting is not effective.",
            "Polityka DMARC jest ustawiona na 'none' i nie ustawiono odbiorcy raportów w polu 'rua', co "
            "oznacza, że ustawienie DMARC nie będzie skuteczne.",
        ),
        (
            "SPF record not found in domain referenced from other SPF record",
            "Rekord SPF odwołuje się do domeny, która nie zawiera rekordu SPF. W przypadku odwoływania się do "
            "innych domen za pomocą dyrektyw SPF takich jak 'include' lub 'redirect', domena docelowa powinna również "
            "zawierać rekord SPF.",
        ),
        (
            "Valid SPF record not found",
            "Nie znaleziono poprawnego rekordu SPF. Rekomendujemy używanie wszystkich trzech mechanizmów: "
            "SPF, DKIM i DMARC, aby zmniejszyć szansę, że sfałszowana wiadomość zostanie zaakceptowana "
            "przez serwer odbiorcy.",
        ),
        (
            "SPF record is not syntatically correct",
            "Rekord SPF nie ma poprawnej składni. Prosimy o jego dokładną weryfikację.",
        ),
        (
            "DMARC record is not syntatically correct",
            "Rekord DMARC nie ma poprawnej składni. Prosimy o jego dokładną weryfikację.",
        ),
        (
            "Multiple SPF records found",
            "Wykryto więcej niż jeden rekord SPF. Rekomendujemy pozostawienie jednego z nich - "
            "obecność wielu rekordów może powodować problemy w działaniu niektórych implementacji mechanizmu SPF.",
        ),
        (
            "SPF record includes an endless loop",
            "Rekord SPF zawiera nieskończoną pętlę. Prosimy sprawdzić, czy dyrektywy SPF 'include' lub 'redirect' "
            "nie odwołują się z powrotem do tej samej domeny lub do wcześniejszych domen.",
        ),
        (
            "SPF record includes too many DNS lookups",
            "Rekord SPF powoduje zbyt wiele zapytań DNS. Zapytania DNS są powodowane przez niektóre dyrektywy SPF, takie jak "
            "'mx' czy 'include'. Spefycikacja wymaga, aby liczba zapytań DNS nie przekraczała 10, aby nie powodować nadmiernego "
            "obciążenia serwerów DNS.",
        ),
    ]
}


def translate(
    message: str,
    dictionary: List[Tuple[str, str]],
    nonexistent_translation_handler: Optional[Callable[[str], str]] = None,
) -> str:
    """Translates message according to a dictionary.

    For example, for the following dictionary:

    [
        (f"Input message one {PLACEHOLDER}.", f"Output message one {PLACEHOLDER}."),
        (f"Input message two {PLACEHOLDER}.", f"Output message two {PLACEHOLDER}."),
    ]

    message "Input message one 1234." will get translated to "Output message one 1234.".

    *note* the "from" and "to" messages must have the same number of placeholders -
    and will have the same order of placeholders.
    """
    for m_from, m_to in dictionary:
        pattern = "^" + re.escape(m_from).replace(PLACEHOLDER, "(.*)") + "$"
        regexp_match = re.match(pattern, message)

        # a dictionary rule matched the message
        if regexp_match:
            result = m_to
            for matched in regexp_match.groups():
                # replace first occurence of placeholder with the matched needle
                result = result.replace(PLACEHOLDER, matched, 1)
            return result

    if nonexistent_translation_handler:
        return nonexistent_translation_handler(message)
    else:
        raise NotImplementedError(f"Unable to translate {message}")


def _(
    message: str,
    language: Language,
    nonexistent_translation_handler: Optional[Callable[[str], str]] = None,
) -> str:
    if language == Language.en_US:
        return message

    return translate(
        message,
        TRANSLATIONS[language],
        nonexistent_translation_handler=nonexistent_translation_handler,
    )


def _translate_domain_result(
    domain_result: DomainScanResult,
    language: Language,
    nonexistent_translation_handler: Optional[Callable[[str], str]] = None,
) -> DomainScanResult:
    new_domain_result = copy.deepcopy(domain_result)
    new_domain_result.spf.errors = [
        _(error, language, nonexistent_translation_handler) for error in domain_result.spf.errors
    ]
    new_domain_result.spf.warnings = [
        _(warning, language, nonexistent_translation_handler) for warning in domain_result.spf.warnings
    ]
    new_domain_result.dmarc.errors = [
        _(error, language, nonexistent_translation_handler) for error in domain_result.dmarc.errors
    ]
    new_domain_result.dmarc.warnings = [
        _(warning, language, nonexistent_translation_handler) for warning in domain_result.dmarc.warnings
    ]
    new_domain_result.warnings = [
        _(warning, language, nonexistent_translation_handler) for warning in new_domain_result.warnings
    ]
    return new_domain_result


def _translate_dkim_result(
    dkim_result: DKIMScanResult,
    language: Language,
    nonexistent_translation_handler: Optional[Callable[[str], str]] = None,
) -> DKIMScanResult:
    new_dkim_result = copy.deepcopy(dkim_result)
    new_dkim_result.errors = [_(error, language, nonexistent_translation_handler) for error in dkim_result.errors]
    new_dkim_result.warnings = [
        _(warning, language, nonexistent_translation_handler) for warning in dkim_result.warnings
    ]
    return new_dkim_result


def translate_scan_result(
    scan_result: ScanResult,
    language: Language,
    nonexistent_translation_handler: Optional[Callable[[str], str]] = None,
) -> ScanResult:
    return ScanResult(
        domain=_translate_domain_result(scan_result.domain, language, nonexistent_translation_handler)
        if scan_result.domain
        else None,
        dkim=_translate_dkim_result(scan_result.dkim, language, nonexistent_translation_handler)
        if scan_result.dkim
        else None,
        timestamp=scan_result.timestamp,
        message_timestamp=scan_result.message_timestamp,
    )