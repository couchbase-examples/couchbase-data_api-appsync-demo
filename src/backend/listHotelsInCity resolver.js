import { util } from '@aws-appsync/utils';

export function request(ctx) {
    const id = ctx.args.id
    const bucket = "travel-sample"
    const scope = "inventory"
    const collection = "hotel"
    const username = ctx.env.cb_username
    const password = ctx.env.cb_password
    const token = util.base64Encode(`${username}:${password}`)
    const auth = `Basic ${token}`
    const sql_query = `
      WITH airport_loc AS (
        SELECT a.geo.lat AS alat, 
               a.geo.lon AS alon, 
               IFMISSINGORNULL(a.geo.accuracy, "APPROXIMATE") AS accuracy
        FROM airport AS a
        WHERE a.airportname = $1
        LIMIT 1
      )
      SELECT h.*, airport_loc.alat, airport_loc.alon, airport_loc.accuracy
      FROM hotel AS h, airport_loc
      WHERE airport_loc.alat IS NOT MISSING
        AND POWER(h.geo.lat - airport_loc.alat, 2)
          + POWER(h.geo.lon - airport_loc.alon, 2) <= POWER($2 / 111, 2)
    `;



    // Log to CloudWatch for debugging (best practice)
    console.log("Request Context:", ctx)
    
    const requestObject = {
        method: 'POST',
        resourcePath: `/_p/query/query/service`,
        params: {
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': auth
            },
            body: {
                query_context: `default:${bucket}.${scope}`,
                statement: sql_query,
                args: [ctx.arguments.airportName, ctx.arguments.withinKm],
                timeout: "30m"
            }
        }
    }
    
    // Log the outgoing request
    console.log("Outgoing Request to Data API:", requestObject)
    
    return requestObject;
}

export function response(ctx) {
    // Log the complete response context
    console.log("Response Context:", ctx)
        
    // Parse the response body if it's a string
    let parsedResult = ctx.result.body;
    if (typeof ctx.result.body === 'string') {
        parsedResult = JSON.parse(ctx.result.body);
        console.log("Parsed Result:", parsedResult)
    }
    
    const results = parsedResult.results || [];
    
    // Extract airport information from the first result (all results have the same airport location)
    let airport = null;
    if (results.length > 0) {
        const first = results[0];
        airport = {
            name: ctx.arguments.airportName,
            location: {
                lat: first.alat,
                lon: first.alon,
                accuracy: first.accuracy
            }
        };
    }
    
    // Clean up hotels by removing airport location fields
    const hotels = results.map(hotel => {
        const { alat, alon, accuracy, ...cleanHotel } = hotel;
        return cleanHotel;
    });
    
    // Return in the Output schema format
    return {
        hotels: hotels,
        airport: airport
    };
}