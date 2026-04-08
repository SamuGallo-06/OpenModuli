const newFormDialog = document.getElementById('dialog-new-form');
const newFormBtn = document.getElementById("new-form-dialog-confirm")

const uploadFormDialog = document.getElementById('dialog-upload-form');
const uploadFormBtn = document.getElementById("upload-form-dialog-confirm")


function onNewFormClicked() {
    newFormDialog.showModal();
    // Intercetta il submit del form, non il click del bottone
    document.getElementById('new-form-dialog-confirm').onclick = () => {
        const formName = document.getElementById('new-form-name').value;
        if (formName) {
            newFormDialog.close();
        }
    };
}

function onUploadFormClicked(){
    uploadFormDialog.showModal();
    // Intercetta il submit del form, non il click del bottone
    document.getElementById('upload-form-dialog-confirm').onclick = () => {
        const formName = document.getElementById('upload-form-name').value;
        if (formName) {
            //** No Extra redirect. this is controlled by flask */
            uploadFormDialog.close();
        }
    };
}

function onSettingsClicked(){
    window.location.href = '/admin/settings';
}

function onLogoutClicked(){
    window.location.href = '/logout';
}

function onReloadConfigurationClicked(){
    
}

function onRebootApplicationClicked(){
    
}

function onRebootServerClicked(){
    
}

function onShutdownServerClicked(){
    
}

function onDocumentationClicked(){
    window.location.href = '../docs/html/index.html';
}

function onContactSupportClicked(){
    window.location.href = 'mailto:samu.gallicani@gmail.com';
}

function onGitHubRepoClicked(){
    window.location.href = 'https://github.com/SamuGallo-06/OpenModuli';
}

function onLicenceClicked(){
    window.location.href = '/about/license';
}

function onAboutClicked(){
    window.location.href = '/about/about';
}

function onOpenPdfFolderClicked(){
    window.location.href = '/admin/open_pdf_folder';
}