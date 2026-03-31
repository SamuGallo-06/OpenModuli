const dialog = document.getElementById('dialog-delete');
const nomeFile = document.getElementById('dialog-filename');
const btnConferma = document.getElementById('dialog-confirm');

function openDeleteFileDialog(nome) {
  nomeFile.textContent = nome;
  dialog.showModal();

  btnConferma.onclick = () => {
    //** Here goes the deletion logic, e.g., fetch or redirect */
    console.log('Eliminato:', nome);
    dialog.close();
  };
}

function openNewFileDialog(nome) {
  nomeFile.textContent = nome;
  dialog.showModal();

  btnConferma.onclick = () => {
    //** Here goes the redirect to form editor, given the form name as a parameter */
    console.log('Nuovo file:', nome);
    dialog.close();
  };
}

document.getElementById('dialog-delete-discard').onclick = () => dialog.close();
document.getElementById('dialog-new-form-discard').onclick = () => 
    document.getElementById('dialog-new-form').close();