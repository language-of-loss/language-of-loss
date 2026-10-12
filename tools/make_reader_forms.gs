var KIT = /*@@KIT_DATA@@*/null;

var CONSENT_ITEM = 'I am 18 or older, I read both Hindi and English, and I agree to take part';
var SKIP_CHOICE = 'Skip this passage (I would rather not rate it)';
var AGE_BANDS = ['18-24', '25-34', '35-44', '45-54', '55-64', '65 or older', 'Prefer not to say'];
var LANG_CHOICES = ['Hindi', 'English', 'Both equally', 'Prefer not to say'];

function plain(md) {

  return String(md || '').replace(/^#+\s*/gm, '').replace(/\*\*/g, '').replace(/(^|\s)_(\S)/g, '$1$2');
}

function noIdentity(form) {
  try { form.setEmailCollectionType(FormApp.EmailCollectionType.DO_NOT_COLLECT); } catch (e) {
    form.setCollectEmail(false);
  }
  try { form.setRequireLogin(false); } catch (e) {  }
  form.setLimitOneResponsePerUser(false);
  form.setAllowResponseEdits(false);
  form.setPublishingSummary(false);
  form.setShowLinkToRespondAgain(false);
}

function scale(form, title, lo, hi, loLabel, hiLabel, help) {
  var item = form.addScaleItem();
  try { item.setTitle(title); } catch (e) {
    item.setTitle(title.split(']')[0] + ']');
    help = title.slice(title.indexOf(']') + 1).trim() + (help ? '\n\n' + help : '');
  }
  item.setBounds(lo, hi).setLabels(loLabel, hiLabel).setRequired(true);
  if (help) item.setHelpText(help);
  return item;
}

function buildForm(block) {
  var form = FormApp.create(KIT.title + block);
  noIdentity(form);
  form.setProgressBar(true);
  form.setDescription('Grief reading study. About 25 minutes.');

  form.addSectionHeaderItem().setTitle('Information and consent').setHelpText(plain(KIT.consent));
  form.addCheckboxItem().setTitle('Consent').setChoiceValues([CONSENT_ITEM]).setRequired(true);

  form.addPageBreakItem().setTitle('Part 1: passages')
      .setHelpText(plain(KIT.instructions.passages));
  KIT.blocks[String(block)].forEach(function (p) {
    scale(form, '[' + p.code + '] ' + p.text, 1, 7, 'Barely any grief', 'Overwhelming grief',
          '1 = barely any grief, 4 = clear, moderate grief, 7 = overwhelming grief');
    form.addCheckboxItem().setTitle('[' + p.code + ' skip]').setChoiceValues([SKIP_CHOICE]).setRequired(false);
  });

  form.addPageBreakItem().setTitle('Part 2: replies')
      .setHelpText(plain(KIT.instructions.replies));
  KIT.replies.forEach(function (r) {
    scale(form, '[' + r.code + '] Someone wrote:\n\n' + r.passage + '\n\nThe assistant replied:\n\n' + r.reply,
          1, 5, 'Misses the grief entirely', 'Fully recognises the grief',
          '1 = misses the grief entirely, 3 = partly recognises it, 5 = fully recognises it and responds to it');
  });

  form.addPageBreakItem().setTitle('Part 3: about you (optional)');
  form.addMultipleChoiceItem().setTitle('Age band').setChoiceValues(AGE_BANDS).setRequired(false);
  form.addMultipleChoiceItem().setTitle('Which language do you read more comfortably?')
      .setChoiceValues(LANG_CHOICES).setRequired(false);

  form.setConfirmationMessage('Thank you. Your answers have been recorded without your name or e-mail.');
  var sheet = SpreadsheetApp.create(KIT.title + block + ' (Responses)');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());
  return {block: block, respond: form.getPublishedUrl(), edit: form.getEditUrl(), sheet: sheet.getUrl()};
}

function makeReaderForms() {
  if (!KIT) throw new Error('KIT is empty: use docs/reader_study/make_reader_forms.gs (written by make reader-kit)');
  if (KIT.replies.length !== 10) Logger.log('WARNING: ' + KIT.replies.length + ' reply exchanges (10 planned)');
  Object.keys(KIT.blocks).sort(function (a, b) { return a - b; }).forEach(function (b) {
    var r = buildForm(Number(b));
    Logger.log('Block ' + r.block + '\n  participants: ' + r.respond + '\n  edit: ' + r.edit + '\n  responses: ' + r.sheet);
  });
}
