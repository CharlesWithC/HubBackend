function getUrlParameter(sParam) {
  var sPageURL = window.location.search.substring(1),
    sURLVariables = sPageURL.split('&'),
    sParameterName,
    i;

  for (i = 0; i < sURLVariables.length; i++) {
    sParameterName = sURLVariables[i].split('=');

    if (sParameterName[0] === sParam) {
      return sParameterName[1] === undefined ? true : decodeURIComponent(sParameterName[1]);
    }
  }
  return false;
};

function toastFactory(type, title, text, time, showConfirmButton) {
  const Toast = Swal.mixin({
      toast: true,
      position: 'top-start',
      showConfirmButton: showConfirmButton || false,
      timer: time || '3000',
      timerProgressBar: true,
      didOpen: (toast) => {
          toast.addEventListener('mouseenter', Swal.stopTimer);
          toast.addEventListener('mouseleave', Swal.resumeTimer);
      },
  });

  Toast.fire({
      icon: type,
      title: '<strong>' + title + '</strong>',
      html: text,
  });
}

function getCookie(cookiename) {
  // Get name followed by anything except a semicolon
  var cookiestring = RegExp(cookiename + "=[^;]+").exec(document.cookie);
  // Return everything after the equal sign, or an empty string if the cookie name not found
  return decodeURIComponent(!!cookiestring ? cookiestring.toString().replace(/^[^=]+./, "") : "");
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function genBanner(btype, title, content) {
  if (btype == "info") {
    return `
        <div class="py-8 px-6" style="width:100%">
          <div class="p-6 border-l-4 border-2 border-indigo-500 rounded-r-lg bg-gray-50">
            <div class="flex">
              <div class="w-auto">
                <span class="w-auto inline-block mr-2">
                  <svg width="20" height="20" viewbox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10 0C4.5 0 0 4.5 0 10C0 15.5 4.5 20 10 20C15.5 20 20 15.5 20 10C20 4.5 15.5 0 10 0ZM11 14C11 14.6 10.6 15 10 15C9.4 15 9 14.6 9 14V10C9 9.4 9.4 9 10 9C10.6 9 11 9.4 11 10V14ZM10 7C9.4 7 9 6.6 9 6C9 5.4 9.4 5 10 5C10.6 5 11 5.4 11 6C11 6.6 10.6 7 10 7Z" fill="#382CDD"></path>
                  </svg>
                </span>
              </div>
              <div class="w-full">
                <div class="flex">
                  <h3 class="text-indigo-800 font-medium">` + title + `</h3>
                </div>
                <div class="pr-6">
                  <p class="text-sm text-indigo-700">` + content + `</p>
                </div>
              </div>
            </div>
          </div>
        </div>`;
  } else if (btype == "criticle") {
    return `
        <div class="py-8 px-6" style="width:100%">
          <div class="p-6 bg-red-50 border-l-4 border-red-500 rounded-r-lg bg-gray-50">
            <div class="flex">
              <div class="w-auto">
                <span class="w-auto inline-block mr-2">
                  <svg width="20" height="20" viewbox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10 0C4.5 0 0 4.5 0 10C0 15.5 4.5 20 10 20C15.5 20 20 15.5 20 10C20 4.5 15.5 0 10 0ZM10 15C9.4 15 9 14.6 9 14C9 13.4 9.4 13 10 13C10.6 13 11 13.4 11 14C11 14.6 10.6 15 10 15ZM11 10C11 10.6 10.6 11 10 11C9.4 11 9 10.6 9 10V6C9 5.4 9.4 5 10 5C10.6 5 11 5.4 11 6V10Z" fill="#E85444"></path>
                  </svg>
                </span>
              </div>
              <div class="w-full">
                <div class="flex">
                  <h3 class="text-red-800 font-medium">` + title + `</h3>
                </div>
                <div class="pr-6">
                  <p class="text-sm text-red-700">` + content + `</p>
                </div>
              </div>
            </div>
          </div>
        </div>`;
  } else if (btype == "resolved") {
    return `
        <div class="py-8 px-6" style="width:100%">
          <div class="p-6 border-l-4 border-2 border-green-500 rounded-r-lg bg-gray-50">
            <div class="flex">
              <div class="w-auto">
                <span class="w-auto inline-block mr-2">
                  <svg width="20" height="20" viewbox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10 0C4.5 0 0 4.5 0 10C0 15.5 4.5 20 10 20C15.5 20 20 15.5 20 10C20 4.5 15.5 0 10 0ZM14.2 8.3L9.4 13.1C9 13.5 8.4 13.5 8 13.1L5.8 10.9C5.4 10.5 5.4 9.9 5.8 9.5C6.2 9.1 6.8 9.1 7.2 9.5L8.7 11L12.8 6.9C13.2 6.5 13.8 6.5 14.2 6.9C14.6 7.3 14.6 7.9 14.2 8.3Z" fill="#17BB84"></path>
                  </svg>
                </span>
              </div>
              <div class="w-full">
                <div class="flex">
                  <h3 class="text-green-800 font-medium">` + title + `</h3>
                </div>
                <div class="pr-6">
                  <p class="text-sm text-green-700">` + content + `</p>
                </div>
              </div>
            </div>
          </div>
        </div>`;
  } else if (btype == "warning") {
    return `<div class="py-8 px-6" style="width:100%">
            <div class="p-6 border-l-4 border-2 border-orange-500 rounded-r-lg bg-gray-50">
            <div class="flex">
                <div class="w-auto">
                <span class="w-auto inline-block mr-2">
                    <svg width="24" height="20" viewbox="0 0 24 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M22.7 15.5001L14.6 1.50011C13.8 0.100109 11.9 -0.399891 10.5 0.400109C10 0.700109 9.60001 1.10011 9.40001 1.50011L1.30001 15.5001C0.500011 16.9001 1.00001 18.8001 2.40001 19.6001C2.90001 19.9001 3.40001 20.0001 3.90001 20.0001H20C21.7 20.0001 23 18.6001 23 17.0001C23.1 16.4001 22.9 15.9001 22.7 15.5001ZM12 16.0001C11.4 16.0001 11 15.6001 11 15.0001C11 14.4001 11.4 14.0001 12 14.0001C12.6 14.0001 13 14.4001 13 15.0001C13 15.6001 12.6 16.0001 12 16.0001ZM13 11.0001C13 11.6001 12.6 12.0001 12 12.0001C11.4 12.0001 11 11.6001 11 11.0001V7.00011C11 6.40011 11.4 6.00011 12 6.00011C12.6 6.00011 13 6.40011 13 7.00011V11.0001Z" fill="#F67A28"></path>
                    </svg>
                </span>
                </div>
                <div class="w-full">
                <div class="flex">
                    <h3 class="text-orange-800 font-medium">`+title+`</h3>
                </div>
                <div class="pr-6">
                    <p class="text-sm text-orange-700">`+content+`</p>
                </div>
                </div>
            </div>
            </div>
        </div>
        </div>`;
  }
}

function pad(num, size) {
  var s = num+"";
  while (s.length < size) s = "0" + s;
  return s;
}

function getDateTime(timestamp) {
  dt = new Date(timestamp);
  MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  date = dt.getDate();
  if(date == 1){
    date = "1st";
  } else if(date == 2){
    date = "2nd";
  } else if(date == 3){
    date = "3rd";
  } else if(date == 21){
    date = "21st";
  } else if(date == 22){
    date = "22nd";
  } else if(date == 23){
    date = "23rd";
  } else if(date == 31){
    date = "31st";
  } else {
    date = date + "th";
  }
  return pad(dt.getHours(),2) + ":" + pad(dt.getMinutes(),2) + ", " + MONTHS[dt.getMonth()] + " " + date + " " + dt.getFullYear();
}

function isNumber(n) {
  return /^-?[\d.]+(?:e-?\d+)?$/.test(n);
}

// Calculates significant figures with suffixes K/M/B/T, e.g. 1234 = 1.23K
function sigfig(num, sigfigs_opt) {
  flag = ""
  if(num < 0) flag = "-", num=-num;
  // Set default sigfigs to 3
  sigfigs_opt = (typeof sigfigs_opt === "undefined") ? 3 : sigfigs_opt;
  // Only assigns sig figs and suffixes for numbers > 1
  if (num <= 1) return num.toPrecision(sigfigs_opt);
  // Calculate for numbers > 1
  var power10 = log10(num);
  var power10ceiling = Math.floor(power10) + 1;
  // 0 = '', 1 = 'K', 2 = 'M', 3 = 'B', 4 = 'T'
  var SUFFIXES = ['', 'K', 'M', 'B', 'T'];
  // 100: power10 = 2, suffixNum = 0, suffix = ''
  // 1000: power10 = 3, suffixNum = 1, suffix = 'K'
  var suffixNum = Math.floor(power10 / 3);
  var suffix = SUFFIXES[suffixNum];
  // Would be 1 for '', 1000 for 'K', 1000000 for 'M', etc.
  var suffixPower10 = Math.pow(10, suffixNum * 3);
  var base = num / suffixPower10;
  var baseRound = base.toPrecision(sigfigs_opt);
  return flag + baseRound + suffix;
}

function log10(num) {
  // Per http://stackoverflow.com/questions/3019278/how-can-i-specify-the-base-for-math-log-in-javascript#comment29970629_16868744
  // Handles floating-point errors log10(1000) otherwise fails at (2.99999996)
  return (Math.round(Math.log(num) / Math.LN10 * 1e6) / 1e6);
}

function TSeparator(num){
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function parseMarkdown(markdownText) {
	const htmlText = markdownText
		.replace(/^### (.*$)/gim, '<h3>$1</h3>')
		.replace(/^## (.*$)/gim, '<h2>$1</h2>')
		.replace(/^# (.*$)/gim, '<h1>$1</h1>')
		.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
		.replace(/\*\*(.*)\*\*/gim, '<b>$1</b>')
		.replace(/\*(.*)\*/gim, '<i>$1</i>')
		.replace(/!\[(.*?)\]\((.*?)\)/gim, "<img alt='$1' src='$2' />")
		.replace(/\[(.*?)\]\((.*?)\)/gim, "<a href='$2' style='text-decoration:underline' target='_blank'>$1</a>")
		.replace(/\n$/gim, '<br>')
    .replace(/  /gim, '<br>')

	return htmlText.trim()
}

RANKING = localStorage.getItem("rankname");
if(RANKING == null){
  RANKING = [];
  $.ajax({
    url: "https://drivershub.charlws.com/atm/member/ranks",
    type: "GET",
    dataType: "json",
    success: function (data) {
        RANKING = data.response;
        localStorage.setItem("rankname", JSON.stringify(RANKING));
    }
  });
} else {
  RANKING = JSON.parse(RANKING);
}

function point2rank(point){
  keys = Object.keys(RANKING);
  for(var i = 0; i < keys.length; i++){
    if(point < keys[i]){
      return RANKING[keys[i-1]];
    }
  }
  return RANKING[keys[keys.length - 1]];
}

String.prototype.toHHMMSS = function () {
  var sec_num = parseInt(this, 10); // don't forget the second param
  var hours   = Math.floor(sec_num / 3600);
  var minutes = Math.floor((sec_num - (hours * 3600)) / 60);
  var seconds = sec_num - (hours * 3600) - (minutes * 60);

  if (hours   < 10) {hours   = "0"+hours;}
  if (minutes < 10) {minutes = "0"+minutes;}
  if (seconds < 10) {seconds = "0"+seconds;}
  return hours + ':' + minutes + ':' + seconds;
}

function b62decode(num62) {
    flag = 1;
    if(num62.startsWith("-")) {
        flag = -1;
        num62 = num62.slice(1);
    }
    ret = 0;
    l = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
    for(i = 0; i < num62.length; i++) {
        ret += l.indexOf(num62[i]) * 62 ** (num62.length - i - 1);
    }
    return ret * flag;
}