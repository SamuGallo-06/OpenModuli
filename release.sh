#!/bin/bash

# OpenModuli Release Script
# Automatizza il processo di creazione di una release

set -e  # Exit on error

# Colori per l'output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzioni di utilità
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Verifica che sia stata fornita la versione
if [ -z "$1" ]; then
    print_error "Errore: Versione non fornita"
    echo "Uso: $0 <versione>"
    echo "Esempio: $0 1.0.0"
    exit 1
fi

VERSION=$1
DATE=$(date +"%Y-%m-%d")
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

print_header "OpenModuli Release v$VERSION"

# Verifica il branch
print_info "Branch corrente: $CURRENT_BRANCH"
if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
    print_warning "Non sei sul branch main/master!"
    read -p "Vuoi continuare comunque? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        print_error "Release annullata"
        exit 1
    fi
fi

# Verifica che non ci siano uncommitted changes
print_info "Verifica working directory..."
if ! git diff-index --quiet HEAD --; then
    print_error "Ci sono file modificati non committati!"
    git status
    exit 1
fi
print_success "Working directory pulita"

# Verifica che il tag non esista già
print_info "Verifica esistenza tag..."
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    print_error "Il tag v$VERSION esiste già!"
    exit 1
fi
print_success "Tag non esiste (ok)"

# Aggiorna version.py
print_info "Aggiornamento version.py..."
cat > version.py << EOF
"""OpenModuli version information."""

__version__ = "$VERSION"
__author__ = "Samuele Gallicani"
__license__ = "AGPL-3.0"
EOF
print_success "version.py aggiornato"

# Verifica/crea CHANGELOG.md
if [ ! -f "CHANGELOG.md" ]; then
    print_info "CHANGELOG.md non esiste, creato..."
    cat > CHANGELOG.md << 'EOF'
# Changelog

Tutti i cambiamenti notevoli di questo progetto saranno documentati in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/),
e questo progetto segue il [Versionamento Semantico](https://semver.org/it/).

## [1.0.0] - 2026-04-30

### Added
- Supporto completo per la creazione di form personalizzati
- Esportazione PDF dei dati raccolti
- Sistema di gestione utenti e autenticazione
- Integrazione Google Forms API
- Branding personalizzabile
- Sistema di scripting Python per validazione
- Documentazione con Doxygen

### Changed
- Miglioramenti nell'interfaccia del form builder
- Ottimizzazione della generazione PDF

### Fixed
- Corretto footer nei PDF generati
- Migliorato handling dei percorsi normalizzati
- Corretti elementi UI nei template
EOF
    print_success "CHANGELOG.md creato"
fi

# Stage dei file
print_info "Stage dei file..."
git add version.py CHANGELOG.md
print_success "File staged"

# Commit
print_info "Creazione commit..."
git commit -m "Release v$VERSION: Stable release"
print_success "Commit creato"

# Tag
print_info "Creazione tag annotato..."
git tag -a "v$VERSION" -m "Release version $VERSION - Stable release ($(date +%Y-%m-%d))"
print_success "Tag v$VERSION creato"

print_header "Release Summary"
print_info "Versione: v$VERSION"
print_info "Data: $DATE"
print_info "Branch: $CURRENT_BRANCH"
echo ""
print_info "Commit e tag creati localmente."
echo ""
print_warning "Prossimi passaggi (manuali):"
echo "  1. Verifica i cambiamenti: git log -1"
echo "  2. Push del commit:        git push origin $CURRENT_BRANCH"
echo "  3. Push del tag:          git push origin v$VERSION"
echo "  4. O spingere tutto:      git push origin $CURRENT_BRANCH --tags"
echo ""
read -p "Vuoi fare il push ora? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    print_info "Push in corso..."
    git push origin "$CURRENT_BRANCH"
    print_success "Branch pushato"
    git push origin "v$VERSION"
    print_success "Tag pushato"
    print_header "✓ Release Completata!"
    print_success "v$VERSION è ora disponibile su GitHub"
else
    print_warning "Push saltato"
    print_info "Ricorda di fare il push manualmente quando pronto"
fi

print_success "Release v$VERSION completata!"
