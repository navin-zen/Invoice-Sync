/**
 * Wrapper around fetch API
 */

export function fetchWrapper(url: string, params: RequestInit): Promise<Response> {
  return new Promise((resolve, reject) => {
    fetch(url, params)
      .then((response) => {
        if (!response.ok) {
          reject(Error(response.statusText));
        }
        resolve(response);
      })
      .catch((error) => {
        reject(error);
      });
  });
}

export function httpGet(url: string) {
  return fetchWrapper(url, {
    // As per https://medium.com/@shahata/why-i-wont-be-using-fetch-api-in-my-apps-6900e6c6fe78
    // only if we have credentials = include, Microsoft Edge will send cookies along with the request
    credentials: "include",
  });
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Retrive contents from `url`
 *
 * If url returns a deferred output (HTTP status code 202),
 * then we wait until the output is ready.
 *
 * Returns a promise
 *
 * @param url - The URL to retrieve contents from.
 * @param delayList - The delay between polls to see if the content is ready
 */
export function httpPotentialDeferredGet(url: string, delayList?: Array<number>): Promise<Response> {
  return new Promise((resolve, reject) => {
    httpGet(url)
      .then((possibleResponse) => {
        if (possibleResponse.status !== 202) {
          resolve(possibleResponse);
          return;
        }
        possibleResponse.json().then(
          async (data: {
            token: string;
            url: string;
          }) => {
            const defaultDelayList = [
              1000, 2000, 3000, 4000, 5000, 6000, 20000, 20000, 20000, 20000, 20000, 20000, 20000, 20000, 20000, 20000,
            ];
            for (const delay of delayList || defaultDelayList) {
              await sleep(delay);
              try {
                const response = await httpGet(data.url);
                resolve(response);
                return;
              } catch {
                // Don't do anything if the httpGet fails
              }
            }
            reject(Error("Trying to get response. Too many attempts.."));
          },
        );
      })
      .catch((error) => {
        reject(error);
      });
  });
}

export function httpPut(url: string, body: any) {
  const params: RequestInit = {
    method: "PUT",
    cache: "no-cache",
    body: body,
  };
  return fetchWrapper(url, params);
}

export function httpPost(url: string, body: any, content_type: string): Promise<Response> {
  const params: RequestInit = {
    method: "POST",
    mode: "cors",
    cache: "no-cache",
    headers: [
      ["Content-Type", content_type],
      // ["X-CSRFToken", GSTZEN_CONSTANTS.CSRF_TOKEN],
    ],
    body: body,
    // As per https://medium.com/@shahata/why-i-wont-be-using-fetch-api-in-my-apps-6900e6c6fe78
    // only if we have credentials = include, Microsoft Edge will send cookies along with the request
    credentials: "include",
  };
  return fetchWrapper(url, params);
}

export function httpPostFormData(url: string, body: any) {
  return httpPost(url, body, "application/x-www-form-urlencoded");
}

/**
 * Make a POST request which does not trigger a CORS preflight check.
 *
 * This function makes a simple request:
 * https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#Simple_requests
 */
export function httpSimplePost(url: string, body: any, content_type: string) {
  const params: RequestInit = {
    method: "POST",
    mode: "cors",
    cache: "no-cache",
    headers: [["Content-Type", content_type]],
    body: body,
  };
  return fetchWrapper(url, params);
}

/**
 * Make a GET request which does not have credentials: include
 *
 * We add credentials: include so that it works with Edge on our regular
 * website. However, with Tally, we get the error:
 *
 *  Access to fetch at 'http://localhost:9000/' from origin
 * 'http://localhost:9001' has been blocked by CORS policy: The value of the
 * 'Access-Control-Allow-Origin' header in the response must not be the wildcard
 * '*' when the request's credentials mode is 'include'.
 */
export function httpSimpleGet(url: string) {
  return fetchWrapper(url, {});
}

export function lookupHeader(needle: string, headers: Array<[string, string]>): string {
  for (const row of headers) {
    const [header, value] = row;
    if (header.toLowerCase() == needle.toLowerCase()) {
      return value;
    }
  }
  return "";
}

export function lookupContentType(headers: Array<[string, string]>): string {
  return lookupHeader("content-type", headers);
}
