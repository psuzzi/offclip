"""User-interface languages. English is the reference; the others are translations of it.

Adding a language: copy the "it" dictionary under a new code, translate the values, and add the code to
LANGUAGES. Missing keys fall back to English at run time, but problems() (run by the selftest in CI) wants every
key and the same {placeholders} as English. Keep labels short: buttons, column headers and the status column.
The language follows the operating system unless settings.json says "language": "<code>".
Translations other than English and Italian are machine-assisted; native-speaker corrections are welcome.
"""
from __future__ import annotations

import locale
import os
import string
import subprocess
import sys

LANGUAGES = {"en": "English", "it": "Italiano", "de": "Deutsch", "fr": "Français", "es": "Español",
             "pt": "Português", "nl": "Nederlands", "pl": "Polski"}

STRINGS = {
    "en": {
        "title": "Download from YouTube",
        "add_link": "Add link",
        "search_label": "Looking for a video? Search on YouTube in your browser:",
        "search_btn": "Search",
        "paste_placeholder": "Paste a YouTube link here and press Enter, or drop links onto the table",
        "paste_placeholder_short": "Paste a YouTube link, Enter",
        "col_quality": "Quality", "col_link": "Link", "col_title": "Title", "col_channel": "Channel", "col_status": "Status",
        "hint_dnd": "No links yet. Drop them here, or paste one above.",
        "hint": "No links yet. Paste one above.",
        "choose_folder": "Choose folder…",
        "open_folder": "Open folder",
        "save_to": "Save to: {path}",
        "save_dialog": "Save downloads to…",
        "download": "Download",
        "clear_completed": "Clear completed",
        "open_file": "open", "tip_open_file": "Show in the folder:",
        "max_rows": "At most {n} links at a time.",
        "st_fetching": "fetching info…", "st_ready": "ready", "st_error": "error", "st_done": "done ✓",
        "st_downloading": "downloading…", "st_processing": "processing…", "st_retrying": "retrying ({n}/{total})…",
        "tip_info": "Versions and updates", "tip_report": "Report a problem",
        "menu_file": "File", "menu_help": "Help", "menu_quit": "Quit", "menu_language": "Language", "menu_system": "System language",
        "menu_check": "Check for updates…", "menu_report": "Report a problem…", "menu_about": "About offclip",
        "language_changed": "The new language is used from the next start of offclip.",
        "tagline": "Save public clips for personal offline use.",
        "upd_available": "offclip {new} is available (you have {cur}).",
        "upd_latest": "You have the latest version.", "upd_latest_v": "You have the latest version ({cur}).",
        "upd_unknown": "No update known yet.",
        "upd_now": "Update now", "whats_new": "What's new", "check_updates": "Check for updates",
        "updating": "Updating… {stage}", "upd_downloading": "downloading", "upd_verifying": "verifying", "upd_unpacking": "unpacking",
        "upd_failed": "Update failed: {error}",
        "upd_done_restart": "Updated to {new}. offclip will now restart.",
        "upd_done_manual": "Updated to {new}. Please close and start offclip again.",
        "close": "Close", "cancel": "Cancel",
        "report_title": "Report a problem",
        "report_question": "What happened? A problem, an idea, a question.",
        "report_note": "Your text, the component versions and the last lines of the log are included. Nothing else is sent.",
        "report_send": "Send (opens GitHub)", "report_default_title": "Report from offclip",
    },
    "it": {
        "title": "Scarica da YouTube",
        "add_link": "Aggiungi link",
        "search_label": "Cerchi un video? Cerca su YouTube nel browser:",
        "search_btn": "Cerca",
        "paste_placeholder": "Incolla qui un link di YouTube e premi Invio, oppure trascina i link nella tabella",
        "paste_placeholder_short": "Incolla un link di YouTube, Invio",
        "col_quality": "Qualità", "col_link": "Link", "col_title": "Titolo", "col_channel": "Canale", "col_status": "Stato",
        "hint_dnd": "Nessun link per ora. Trascinali qui, oppure incollane uno qui sopra.",
        "hint": "Nessun link per ora. Incollane uno qui sopra.",
        "choose_folder": "Scegli cartella…",
        "open_folder": "Apri cartella",
        "save_to": "Salva in: {path}",
        "save_dialog": "Salva i download in…",
        "download": "Scarica",
        "clear_completed": "Svuota completate",
        "open_file": "apri", "tip_open_file": "Mostra nella cartella:",
        "max_rows": "Al massimo {n} link alla volta.",
        "st_fetching": "recupero info…", "st_ready": "pronto", "st_error": "errore", "st_done": "fatto ✓",
        "st_downloading": "scaricamento…", "st_processing": "elaborazione…", "st_retrying": "nuovo tentativo ({n}/{total})…",
        "tip_info": "Versioni e aggiornamenti", "tip_report": "Segnala un problema",
        "menu_file": "File", "menu_help": "Aiuto", "menu_quit": "Esci", "menu_language": "Lingua", "menu_system": "Lingua di sistema",
        "menu_check": "Cerca aggiornamenti…", "menu_report": "Segnala un problema…", "menu_about": "Informazioni su offclip",
        "language_changed": "La nuova lingua sarà usata dal prossimo avvio di offclip.",
        "tagline": "Salva clip pubbliche per uso personale offline.",
        "upd_available": "È disponibile offclip {new} (hai la {cur}).",
        "upd_latest": "Hai l'ultima versione.", "upd_latest_v": "Hai l'ultima versione ({cur}).",
        "upd_unknown": "Nessun aggiornamento noto per ora.",
        "upd_now": "Aggiorna ora", "whats_new": "Novità", "check_updates": "Cerca aggiornamenti",
        "updating": "Aggiornamento… {stage}", "upd_downloading": "scaricamento", "upd_verifying": "verifica", "upd_unpacking": "estrazione",
        "upd_failed": "Aggiornamento non riuscito: {error}",
        "upd_done_restart": "Aggiornato alla {new}. offclip verrà riavviato.",
        "upd_done_manual": "Aggiornato alla {new}. Chiudi e riapri offclip.",
        "close": "Chiudi", "cancel": "Annulla",
        "report_title": "Segnala un problema",
        "report_question": "Cosa è successo? Un problema, un'idea, una domanda.",
        "report_note": "Vengono inclusi il tuo testo, le versioni dei componenti e le ultime righe del log. Nient'altro viene inviato.",
        "report_send": "Invia (apre GitHub)", "report_default_title": "Segnalazione da offclip",
    },
    # -- batch 1 (#7): machine-assisted, native-speaker corrections welcome -------------------------------------------
    "de": {
        "title": "Von YouTube herunterladen",
        "add_link": "Link hinzufügen",
        "search_label": "Auf der Suche nach einem Video? Im Browser auf YouTube suchen:",
        "search_btn": "Suchen",
        "paste_placeholder": "YouTube-Link hier einfügen und Enter drücken, oder Links auf die Tabelle ziehen",
        "paste_placeholder_short": "YouTube-Link einfügen, Enter",
        "col_quality": "Qualität", "col_link": "Link", "col_title": "Titel", "col_channel": "Kanal", "col_status": "Status",
        "hint_dnd": "Noch keine Links. Hierher ziehen oder oben einen einfügen.",
        "hint": "Noch keine Links. Oben einen einfügen.",
        "choose_folder": "Ordner wählen…",
        "open_folder": "Ordner öffnen",
        "save_to": "Speichern in: {path}",
        "save_dialog": "Downloads speichern in…",
        "download": "Herunterladen",
        "clear_completed": "Fertige entfernen",
        "open_file": "öffnen", "tip_open_file": "Im Ordner zeigen:",
        "max_rows": "Höchstens {n} Links auf einmal.",
        "st_fetching": "Infos abrufen…", "st_ready": "bereit", "st_error": "Fehler", "st_done": "fertig ✓",
        "st_downloading": "wird geladen…", "st_processing": "Verarbeitung…", "st_retrying": "neuer Versuch ({n}/{total})…",
        "tip_info": "Versionen und Updates", "tip_report": "Problem melden",
        "menu_file": "Datei", "menu_help": "Hilfe", "menu_quit": "Beenden", "menu_language": "Sprache", "menu_system": "Systemsprache",
        "menu_check": "Nach Updates suchen…", "menu_report": "Problem melden…", "menu_about": "Über offclip",
        "language_changed": "Die neue Sprache gilt ab dem nächsten Start von offclip.",
        "tagline": "Öffentliche Clips für die private Offline-Nutzung speichern.",
        "upd_available": "offclip {new} ist verfügbar (installiert: {cur}).",
        "upd_latest": "Die neueste Version ist installiert.", "upd_latest_v": "Die neueste Version ist installiert ({cur}).",
        "upd_unknown": "Noch kein Update bekannt.",
        "upd_now": "Jetzt aktualisieren", "whats_new": "Neuigkeiten", "check_updates": "Nach Updates suchen",
        "updating": "Aktualisierung… {stage}", "upd_downloading": "Download", "upd_verifying": "Prüfung", "upd_unpacking": "Entpacken",
        "upd_failed": "Aktualisierung fehlgeschlagen: {error}",
        "upd_done_restart": "Auf {new} aktualisiert. offclip wird jetzt neu gestartet.",
        "upd_done_manual": "Auf {new} aktualisiert. Bitte offclip schließen und neu starten.",
        "close": "Schließen", "cancel": "Abbrechen",
        "report_title": "Problem melden",
        "report_question": "Was ist passiert? Ein Problem, eine Idee, eine Frage.",
        "report_note": "Mitgesendet werden der Text, die Versionen der Komponenten und die letzten Zeilen des Protokolls. Sonst nichts.",
        "report_send": "Senden (öffnet GitHub)", "report_default_title": "Meldung aus offclip",
    },
    "fr": {
        "title": "Télécharger depuis YouTube",
        "add_link": "Ajouter le lien",
        "search_label": "Vous cherchez une vidéo ? Cherchez sur YouTube dans votre navigateur :",
        "search_btn": "Rechercher",
        "paste_placeholder": "Collez ici un lien YouTube et appuyez sur Entrée, ou déposez des liens sur le tableau",
        "paste_placeholder_short": "Collez un lien YouTube, Entrée",
        "col_quality": "Qualité", "col_link": "Lien", "col_title": "Titre", "col_channel": "Chaîne", "col_status": "État",
        "hint_dnd": "Aucun lien pour l'instant. Déposez-les ici ou collez-en un ci-dessus.",
        "hint": "Aucun lien pour l'instant. Collez-en un ci-dessus.",
        "choose_folder": "Choisir un dossier…",
        "open_folder": "Ouvrir le dossier",
        "save_to": "Enregistrer dans : {path}",
        "save_dialog": "Enregistrer les téléchargements dans…",
        "download": "Télécharger",
        "clear_completed": "Effacer les terminés",
        "open_file": "ouvrir", "tip_open_file": "Afficher dans le dossier :",
        "max_rows": "Au maximum {n} liens à la fois.",
        "st_fetching": "récupération…", "st_ready": "prêt", "st_error": "erreur", "st_done": "terminé ✓",
        "st_downloading": "téléchargement…", "st_processing": "traitement…", "st_retrying": "nouvel essai ({n}/{total})…",
        "tip_info": "Versions et mises à jour", "tip_report": "Signaler un problème",
        "menu_file": "Fichier", "menu_help": "Aide", "menu_quit": "Quitter", "menu_language": "Langue", "menu_system": "Langue du système",
        "menu_check": "Rechercher des mises à jour…", "menu_report": "Signaler un problème…", "menu_about": "À propos d'offclip",
        "language_changed": "La nouvelle langue sera utilisée au prochain démarrage d'offclip.",
        "tagline": "Enregistrez des clips publics pour un usage personnel hors ligne.",
        "upd_available": "offclip {new} est disponible (vous avez la {cur}).",
        "upd_latest": "Vous avez la dernière version.", "upd_latest_v": "Vous avez la dernière version ({cur}).",
        "upd_unknown": "Aucune mise à jour connue pour l'instant.",
        "upd_now": "Mettre à jour", "whats_new": "Nouveautés", "check_updates": "Rechercher des mises à jour",
        "updating": "Mise à jour… {stage}", "upd_downloading": "téléchargement", "upd_verifying": "vérification", "upd_unpacking": "extraction",
        "upd_failed": "Échec de la mise à jour : {error}",
        "upd_done_restart": "Mis à jour vers la {new}. offclip va redémarrer.",
        "upd_done_manual": "Mis à jour vers la {new}. Fermez et relancez offclip.",
        "close": "Fermer", "cancel": "Annuler",
        "report_title": "Signaler un problème",
        "report_question": "Que s'est-il passé ? Un problème, une idée, une question.",
        "report_note": "Votre texte, les versions des composants et les dernières lignes du journal sont joints. Rien d'autre n'est envoyé.",
        "report_send": "Envoyer (ouvre GitHub)", "report_default_title": "Signalement depuis offclip",
    },
    "es": {
        "title": "Descargar de YouTube",
        "add_link": "Añadir enlace",
        "search_label": "¿Buscas un video? Búscalo en YouTube en tu navegador:",
        "search_btn": "Buscar",
        "paste_placeholder": "Pega aquí un enlace de YouTube y presiona Enter, o arrastra enlaces a la tabla",
        "paste_placeholder_short": "Pega un enlace de YouTube, Enter",
        "col_quality": "Calidad", "col_link": "Enlace", "col_title": "Título", "col_channel": "Canal", "col_status": "Estado",
        "hint_dnd": "Aún no hay enlaces. Suéltalos aquí o pega uno arriba.",
        "hint": "Aún no hay enlaces. Pega uno arriba.",
        "choose_folder": "Elegir carpeta…",
        "open_folder": "Abrir carpeta",
        "save_to": "Guardar en: {path}",
        "save_dialog": "Guardar descargas en…",
        "download": "Descargar",
        "clear_completed": "Quitar completadas",
        "open_file": "abrir", "tip_open_file": "Mostrar en la carpeta:",
        "max_rows": "Como máximo {n} enlaces a la vez.",
        "st_fetching": "leyendo info…", "st_ready": "listo", "st_error": "error", "st_done": "hecho ✓",
        "st_downloading": "descargando…", "st_processing": "procesando…", "st_retrying": "reintentando ({n}/{total})…",
        "tip_info": "Versiones y actualizaciones", "tip_report": "Informar de un problema",
        "menu_file": "Archivo", "menu_help": "Ayuda", "menu_quit": "Salir", "menu_language": "Idioma", "menu_system": "Idioma del sistema",
        "menu_check": "Buscar actualizaciones…", "menu_report": "Informar de un problema…", "menu_about": "Acerca de offclip",
        "language_changed": "El nuevo idioma se usará a partir del próximo inicio de offclip.",
        "tagline": "Guarda clips públicos para uso personal sin conexión.",
        "upd_available": "offclip {new} está disponible (tienes la {cur}).",
        "upd_latest": "Tienes la última versión.", "upd_latest_v": "Tienes la última versión ({cur}).",
        "upd_unknown": "Todavía no se conoce ninguna actualización.",
        "upd_now": "Actualizar ahora", "whats_new": "Novedades", "check_updates": "Buscar actualizaciones",
        "updating": "Actualizando… {stage}", "upd_downloading": "descarga", "upd_verifying": "verificación", "upd_unpacking": "extracción",
        "upd_failed": "La actualización falló: {error}",
        "upd_done_restart": "Actualizado a {new}. offclip se reiniciará ahora.",
        "upd_done_manual": "Actualizado a {new}. Cierra y vuelve a abrir offclip.",
        "close": "Cerrar", "cancel": "Cancelar",
        "report_title": "Informar de un problema",
        "report_question": "¿Qué pasó? Un problema, una idea, una pregunta.",
        "report_note": "Se incluyen tu texto, las versiones de los componentes y las últimas líneas del registro. No se envía nada más.",
        "report_send": "Enviar (abre GitHub)", "report_default_title": "Informe desde offclip",
    },
    "pt": {                                              # one dictionary for Portugal and Brazil: neutral wording
        "title": "Download do YouTube",
        "add_link": "Adicionar link",
        "search_label": "Procura um vídeo? Pesquise no YouTube no navegador:",
        "search_btn": "Pesquisar",
        "paste_placeholder": "Cole aqui um link do YouTube e pressione Enter, ou arraste links para a tabela",
        "paste_placeholder_short": "Cole um link do YouTube, Enter",
        "col_quality": "Qualidade", "col_link": "Link", "col_title": "Título", "col_channel": "Canal", "col_status": "Estado",
        "hint_dnd": "Ainda não há links. Arraste-os aqui ou cole um acima.",
        "hint": "Ainda não há links. Cole um acima.",
        "choose_folder": "Escolher pasta…",
        "open_folder": "Abrir pasta",
        "save_to": "Destino: {path}",
        "save_dialog": "Pasta de destino dos downloads…",
        "download": "Download",
        "clear_completed": "Limpar concluídos",
        "open_file": "abrir", "tip_open_file": "Mostrar na pasta:",
        "max_rows": "No máximo {n} links ao mesmo tempo.",
        "st_fetching": "consulta…", "st_ready": "pronto", "st_error": "erro", "st_done": "concluído ✓",
        "st_downloading": "download…", "st_processing": "processamento…", "st_retrying": "nova tentativa ({n}/{total})…",
        "tip_info": "Versões e atualizações", "tip_report": "Reportar um problema",
        "menu_file": "Arquivo", "menu_help": "Ajuda", "menu_quit": "Sair", "menu_language": "Idioma", "menu_system": "Idioma do sistema",
        "menu_check": "Procurar atualizações…", "menu_report": "Reportar um problema…", "menu_about": "Sobre o offclip",
        "language_changed": "O novo idioma será usado da próxima vez que o offclip for aberto.",
        "tagline": "Guarde clipes públicos para uso pessoal offline.",
        "upd_available": "O offclip {new} está disponível (versão atual: {cur}).",
        "upd_latest": "Já tem a versão mais recente.", "upd_latest_v": "Já tem a versão mais recente ({cur}).",
        "upd_unknown": "Ainda não há atualizações conhecidas.",
        "upd_now": "Atualizar agora", "whats_new": "Novidades", "check_updates": "Procurar atualizações",
        "updating": "Atualização… {stage}", "upd_downloading": "download", "upd_verifying": "verificação", "upd_unpacking": "extração",
        "upd_failed": "A atualização falhou: {error}",
        "upd_done_restart": "Atualizado para {new}. O offclip vai reiniciar agora.",
        "upd_done_manual": "Atualizado para {new}. Feche e abra novamente o offclip.",
        "close": "Fechar", "cancel": "Cancelar",
        "report_title": "Reportar um problema",
        "report_question": "O que aconteceu? Um problema, uma ideia, uma pergunta.",
        "report_note": "São incluídos o seu texto, as versões dos componentes e as últimas linhas do log. Nada mais é enviado.",
        "report_send": "Enviar (abre o GitHub)", "report_default_title": "Relatório do offclip",
    },
    "nl": {
        "title": "Downloaden van YouTube",
        "add_link": "Link toevoegen",
        "search_label": "Op zoek naar een video? Zoek op YouTube in je browser:",
        "search_btn": "Zoeken",
        "paste_placeholder": "Plak hier een YouTube-link en druk op Enter, of sleep links naar de tabel",
        "paste_placeholder_short": "Plak een YouTube-link, Enter",
        "col_quality": "Kwaliteit", "col_link": "Link", "col_title": "Titel", "col_channel": "Kanaal", "col_status": "Status",
        "hint_dnd": "Nog geen links. Sleep ze hierheen of plak er een hierboven.",
        "hint": "Nog geen links. Plak er een hierboven.",
        "choose_folder": "Map kiezen…",
        "open_folder": "Map openen",
        "save_to": "Opslaan in: {path}",
        "save_dialog": "Downloads opslaan in…",
        "download": "Downloaden",
        "clear_completed": "Voltooide wissen",
        "open_file": "openen", "tip_open_file": "Tonen in de map:",
        "max_rows": "Maximaal {n} links tegelijk.",
        "st_fetching": "info ophalen…", "st_ready": "gereed", "st_error": "fout", "st_done": "voltooid ✓",
        "st_downloading": "downloaden…", "st_processing": "verwerken…", "st_retrying": "opnieuw ({n}/{total})…",
        "tip_info": "Versies en updates", "tip_report": "Probleem melden",
        "menu_file": "Bestand", "menu_help": "Help", "menu_quit": "Afsluiten", "menu_language": "Taal", "menu_system": "Systeemtaal",
        "menu_check": "Controleren op updates…", "menu_report": "Probleem melden…", "menu_about": "Over offclip",
        "language_changed": "De nieuwe taal wordt gebruikt vanaf de volgende start van offclip.",
        "tagline": "Bewaar openbare clips voor persoonlijk offline gebruik.",
        "upd_available": "offclip {new} is beschikbaar (je hebt {cur}).",
        "upd_latest": "Je hebt de nieuwste versie.", "upd_latest_v": "Je hebt de nieuwste versie ({cur}).",
        "upd_unknown": "Nog geen update bekend.",
        "upd_now": "Nu bijwerken", "whats_new": "Wat is er nieuw", "check_updates": "Controleren op updates",
        "updating": "Bijwerken… {stage}", "upd_downloading": "downloaden", "upd_verifying": "controleren", "upd_unpacking": "uitpakken",
        "upd_failed": "Bijwerken mislukt: {error}",
        "upd_done_restart": "Bijgewerkt naar {new}. offclip wordt nu opnieuw gestart.",
        "upd_done_manual": "Bijgewerkt naar {new}. Sluit offclip en start het opnieuw.",
        "close": "Sluiten", "cancel": "Annuleren",
        "report_title": "Probleem melden",
        "report_question": "Wat is er gebeurd? Een probleem, een idee, een vraag.",
        "report_note": "Je tekst, de versies van de onderdelen en de laatste regels van het logboek worden meegestuurd. Verder niets.",
        "report_send": "Versturen (opent GitHub)", "report_default_title": "Melding vanuit offclip",
    },
    "pl": {
        "title": "Pobierz z YouTube",
        "add_link": "Dodaj link",
        "search_label": "Szukasz filmu? Wyszukaj w YouTube w przeglądarce:",
        "search_btn": "Szukaj",
        "paste_placeholder": "Wklej tutaj link do YouTube i naciśnij Enter albo upuść linki na tabelę",
        "paste_placeholder_short": "Wklej link do YouTube, Enter",
        "col_quality": "Jakość", "col_link": "Link", "col_title": "Tytuł", "col_channel": "Kanał", "col_status": "Stan",
        "hint_dnd": "Brak linków. Upuść je tutaj albo wklej jeden powyżej.",
        "hint": "Brak linków. Wklej jeden powyżej.",
        "choose_folder": "Wybierz folder…",
        "open_folder": "Otwórz folder",
        "save_to": "Zapisz w: {path}",
        "save_dialog": "Zapisuj pobrane pliki w…",
        "download": "Pobierz",
        "clear_completed": "Usuń ukończone",
        "open_file": "otwórz", "tip_open_file": "Pokaż w folderze:",
        "max_rows": "Najwyżej {n} linków naraz.",
        "st_fetching": "odczyt danych…", "st_ready": "do pobrania", "st_error": "błąd", "st_done": "ukończono ✓",
        "st_downloading": "pobieranie…", "st_processing": "przetwarzanie…", "st_retrying": "ponawianie ({n}/{total})…",
        "tip_info": "Wersje i aktualizacje", "tip_report": "Zgłoś problem",
        "menu_file": "Plik", "menu_help": "Pomoc", "menu_quit": "Zakończ", "menu_language": "Język", "menu_system": "Język systemu",
        "menu_check": "Sprawdź aktualizacje…", "menu_report": "Zgłoś problem…", "menu_about": "O programie offclip",
        "language_changed": "Nowy język będzie używany od następnego uruchomienia offclip.",
        "tagline": "Zapisuj publiczne klipy do osobistego użytku offline.",
        "upd_available": "Dostępny jest offclip {new} (masz {cur}).",
        "upd_latest": "Masz najnowszą wersję.", "upd_latest_v": "Masz najnowszą wersję ({cur}).",
        "upd_unknown": "Brak informacji o aktualizacjach.",
        "upd_now": "Aktualizuj teraz", "whats_new": "Co nowego", "check_updates": "Sprawdź aktualizacje",
        "updating": "Aktualizacja… {stage}", "upd_downloading": "pobieranie", "upd_verifying": "weryfikacja", "upd_unpacking": "rozpakowywanie",
        "upd_failed": "Aktualizacja nie powiodła się: {error}",
        "upd_done_restart": "Zaktualizowano do {new}. offclip uruchomi się ponownie.",
        "upd_done_manual": "Zaktualizowano do {new}. Zamknij i uruchom ponownie offclip.",
        "close": "Zamknij", "cancel": "Anuluj",
        "report_title": "Zgłoś problem",
        "report_question": "Co się stało? Problem, pomysł, pytanie.",
        "report_note": "Dołączane są: Twój tekst, wersje komponentów i ostatnie wiersze dziennika. Nic więcej nie jest wysyłane.",
        "report_send": "Wyślij (otwiera GitHub)", "report_default_title": "Zgłoszenie z offclip",
    },
}

_current = "en"


def detect_language() -> str:
    """The operating system's user-interface language, reduced to one of LANGUAGES (default "en")."""
    code = ""
    try:
        if sys.platform == "win32":
            import ctypes
            code = locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), "")
        elif sys.platform == "darwin":
            out = subprocess.run(["defaults", "read", "-g", "AppleLanguages"], capture_output=True, text=True, timeout=3).stdout
            for tok in out.replace("(", " ").replace(")", " ").replace(",", " ").replace('"', " ").split():
                code = tok
                break
    except Exception:
        code = ""
    if not code:
        for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
            if os.environ.get(var):
                code = os.environ[var]
                break
    if not code:
        try:
            code = locale.getlocale()[0] or ""
        except Exception:
            code = ""
    code = code.lower().replace("_", "-")
    for lang in LANGUAGES:
        if code.startswith(lang):
            return lang
    return "en"


def set_language(code: str) -> str:
    """Use `code` ("en", "it"), or the OS language for "auto"/unknown. Returns what is now in use."""
    global _current
    _current = code if code in LANGUAGES else detect_language()
    return _current


def current() -> str:
    return _current


def _fields(text: str) -> set:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}


def problems() -> list:
    """What is wrong with the dictionaries: missing or extra keys, placeholders that differ from English, bad formats."""
    en, out = STRINGS["en"], []
    if set(LANGUAGES) != set(STRINGS):
        out.append(f"LANGUAGES and STRINGS differ: {sorted(set(LANGUAGES) ^ set(STRINGS))}")
    for code, d in STRINGS.items():
        out += [f"{code}: missing {k}" for k in en if k not in d] + [f"{code}: unknown {k}" for k in d if k not in en]
        for k, text in d.items():
            if k in en and _fields(text) != _fields(en[k]):
                out.append(f"{code}.{k}: placeholders {sorted(_fields(text))} instead of {sorted(_fields(en[k]))}")
                continue
            try:
                text.format(**{f: "x" for f in _fields(text)})
            except Exception as e:
                out.append(f"{code}.{k}: {e!r}")
    return out


def t(key: str, **kw) -> str:
    text = STRINGS.get(_current, {}).get(key) or STRINGS["en"].get(key) or key
    return text.format(**kw) if kw else text
