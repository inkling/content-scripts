var fs = require('fs');
const crypto = require('crypto');

if(typeof require !== 'undefined') XLSX = require('xlsx');
var workbook = XLSX.readFile('glossary-data.xlsx');
/* DO SOMETHING WITH workbook HERE */

var sheet_name_list = workbook.SheetNames;
sheet_name_list.forEach(function(y) { /* iterate through sheets */
    var worksheet = workbook.Sheets[y];

    var entry = {
        term: null,
        desc: null,
        output: ''
    }

    const glossary_s9id = crypto.randomBytes(16).toString('hex');

    var glossary = {
        pre: '<?xml version="1.0" encoding="UTF-8"?><glossary xmlns="http://www.standardnine.com/s9ml" designation="Glossary" data-uuid="' + glossary_s9id + '">',
        entrydata: '',
        post: '\n</glossary>',
        output: ''
    };

  glossary.output += glossary.pre;

  for (z in worksheet) {
    /* all keys that do not begin with "!" correspond to cell addresses */
    if(z[0] === '!') continue;

    const col = z.charAt(0);

    if(col == 'A') {
        const s9id = crypto.randomBytes(16).toString('hex');

        entry.output = '';
        entry.term = worksheet[z].v;

        var termSlug = entry.term.replace(/\s+/g, '-').replace(/[\(\)]/g, '').toLowerCase();

        entry.output += '\n<glossentry data-uuid="' + s9id + '">\n'
            + '\t<term key="'+ termSlug +'">'+entry.term+'</term>\n'
            + '\t<definition>\n'
            + '\t\t<title>'+entry.term+'</title>\n'
    }

    if(col == 'B') {
        entry.desc = worksheet[z].v;
        entry.output += '\t\t<text>'+entry.desc+'</text>\n'
            + '\t</definition>\n'
            + '</glossentry>';

        glossary.entrydata += entry.output;
    }
    // console.log(y + "!" + z + "=" + JSON.stringify(worksheet[z].v));
  }

  glossary.output += glossary.entrydata;
  glossary.output += glossary.post;

  fs.writeFile("glossary.s9ml", glossary.output, function(err) {
    if(err) {
        return console.log(err);
    }

    console.log("The file was saved!");
    });

});
