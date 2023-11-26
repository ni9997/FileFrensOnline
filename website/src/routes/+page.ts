import type { PageLoad } from './$types';

export const load: PageLoad = ({ fetch }) => {
	// const res = await fetch('http://localhost:8000/api/files');
	// const files = await res.json();
	// return { files };
    return {
        streamed: {
            files: new Promise<any>(async (fulfil: any) => {
                const res = await fetch('http://localhost:8000/api/files');
                const files = await res.json();
                fulfil(files)
            })
        }
    }
};
